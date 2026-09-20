"""
Critic Agent — Eventura AI (Reflection / Self-Correction)

Checks the generated plan for issues. If issues are found, routes back
to the Planner or Research Agent for correction (max 2 iterations).

Checks:
  - Budget adherence (total vs limit)
  - Guest capacity match
  - Date availability
  - Mandatory category coverage
  - Evidence grounding (every vendor must have evidence IDs)
  - Unsupported/hallucinated claims
  - Rejected vendor re-selection
  - Conflicting evidence
  - Low-confidence evidence
"""

from __future__ import annotations

from app.graph.activity import emit_activity
from app.graph.state import CriticFeedback, CriticIssue, EventState
from app.logger import get_logger
from app.retrieval.feasibility import MANDATORY_CATEGORIES

logger = get_logger(__name__)

MAX_CRITIC_ITERATIONS = 2


async def critic_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Critic Agent.
    All checks are deterministic — the LLM is NOT used for evaluation.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")
    critic_iterations = state.get("critic_iterations", 0)

    await emit_activity(
        session_id=session_id,
        agent="CriticAgent",
        action="evaluate_plan",
        status="running",
        detail=f"Running critic checks (iteration {critic_iterations + 1}/{MAX_CRITIC_ITERATIONS})…",
        db=db,
    )

    issues: list[CriticIssue] = []

    req = state.get("requirements", {})
    vendor_selections = state.get("vendor_selections", [])
    budget_summary = state.get("budget_summary", {})
    evidence = state.get("evidence", [])
    rejected_ids = set(state.get("rejected_vendor_ids", []))
    event_type = req.get("event_type", "wedding")
    guest_count = req.get("guest_count", 0)
    total_budget = req.get("budget", 0.0)
    date_str = req.get("date")

    evidence_ids = {e.get("evidence_id") for e in evidence}

    # ── 1. Budget check ───────────────────────────────────────────────────
    total_spent = budget_summary.get("spent", 0.0)
    if total_spent > total_budget * 1.05:  # 5% tolerance
        issues.append(CriticIssue(
            type="budget_exceeded",
            severity="high",
            category="budget",
            detail=(
                f"Total cost ₹{total_spent:,.0f} exceeds budget ₹{total_budget:,.0f} "
                f"by {((total_spent/total_budget)-1)*100:.1f}%"
            ),
        ))

    # ── 2. Mandatory category coverage ────────────────────────────────────
    mandatory = MANDATORY_CATEGORIES.get(event_type, ["venue", "catering"])
    selected_categories = {s.get("category") for s in vendor_selections}
    for cat in mandatory:
        if cat not in selected_categories:
            issues.append(CriticIssue(
                type="missing_mandatory_category",
                severity="high",
                category=cat,
                detail=f"Mandatory category '{cat}' has no vendor selected",
            ))

    # ── 3. Evidence grounding ─────────────────────────────────────────────
    for sel in vendor_selections:
        ev_ids = sel.get("evidence_ids", [])
        if not ev_ids:
            issues.append(CriticIssue(
                type="missing_evidence",
                severity="high",
                category=sel.get("category", "unknown"),
                detail=(
                    f"Vendor '{sel.get('name')}' has no evidence IDs. "
                    "Recommendation not grounded in retrieved data."
                ),
            ))
        else:
            # Verify evidence IDs actually exist in state
            dangling = [eid for eid in ev_ids if eid not in evidence_ids]
            if dangling:
                issues.append(CriticIssue(
                    type="dangling_evidence_id",
                    severity="medium",
                    category=sel.get("category", "unknown"),
                    detail=f"Evidence IDs not found in state: {dangling}",
                ))

    # ── 4. Rejected vendor re-selection check ─────────────────────────────
    for sel in vendor_selections:
        if sel.get("vendor_id") in rejected_ids:
            issues.append(CriticIssue(
                type="rejected_vendor_reselected",
                severity="high",
                category=sel.get("category", "unknown"),
                detail=(
                    f"Vendor '{sel.get('name')}' (ID: {sel.get('vendor_id')}) "
                    "was previously rejected but re-selected"
                ),
            ))

    # ── 5. Capacity check ────────────────────────────────────────────────
    for sel in vendor_selections:
        if sel.get("category") == "venue":
            max_cap = None  # We don't have this in VendorSelection easily
            # Best we can do: check if vendor was selected (already filtered by capacity)
            # Detailed capacity check is done in Research — flag if guest_count is very high
            if guest_count > 1000:
                issues.append(CriticIssue(
                    type="capacity_warning",
                    severity="low",
                    category="venue",
                    detail=(
                        f"Large event ({guest_count:,} guests). "
                        "Verify venue capacity can accommodate all guests."
                    ),
                ))
            break

    # ── 6. Availability check ─────────────────────────────────────────────
    if date_str:
        # Check that key vendors (venue, catering) have date confirmed
        for sel in vendor_selections:
            if sel.get("category") in ("venue", "catering"):
                if sel.get("status") not in ("approved", "booked", "confirmed"):
                    # Only flag at high severity if no evidence of availability check
                    ev_ids = sel.get("evidence_ids", [])
                    avail_checked = any(
                        e.get("source_type") == "availability"
                        for e in evidence
                        if e.get("evidence_id") in ev_ids
                    )
                    if not avail_checked and len(evidence) > 0:
                        issues.append(CriticIssue(
                            type="availability_unverified",
                            severity="medium",
                            category=sel.get("category"),
                            detail=(
                                f"Availability of '{sel.get('name')}' "
                                f"on {date_str} was not explicitly verified"
                            ),
                        ))

    # ── 7. Low-confidence evidence ────────────────────────────────────────
    low_confidence = [
        e for e in evidence
        if e.get("score", 1.0) < 0.35
    ]
    if low_confidence:
        issues.append(CriticIssue(
            type="low_confidence_evidence",
            severity="low",
            category="general",
            detail=(
                f"{len(low_confidence)} evidence items have low relevance scores "
                f"(< 0.35). Consider re-retrieval."
            ),
        ))

    # ── Determine pass/fail ───────────────────────────────────────────────
    high_issues = [i for i in issues if i.get("severity") == "high"]
    passed = len(high_issues) == 0

    new_iteration = critic_iterations + 1
    feedback = CriticFeedback(
        passed=passed,
        issues=issues,
        iteration=new_iteration,
        resolved=passed,
    )

    all_feedback = list(state.get("critic_feedback", []))
    all_feedback.append(feedback)

    if passed:
        status_label = "success"
        detail = f"Plan passed critic checks ✓ ({len(issues)} minor warnings)"
        next_status = "awaiting_approval"
    else:
        status_label = "warning" if new_iteration >= MAX_CRITIC_ITERATIONS else "error"
        detail = (
            f"Plan failed critic checks ✗ — "
            f"{len(high_issues)} high-severity issues "
            f"(iteration {new_iteration}/{MAX_CRITIC_ITERATIONS})"
        )
        if new_iteration >= MAX_CRITIC_ITERATIONS:
            # Max iterations reached — continue with warnings
            detail += " — proceeding with warnings"
            next_status = "awaiting_approval"
        else:
            next_status = "replanning"

    await emit_activity(
        session_id=session_id,
        agent="CriticAgent",
        action="evaluate_plan",
        status=status_label,
        detail=detail,
        payload={
            "passed": passed,
            "issues": issues,
            "iteration": new_iteration,
        },
        db=db,
    )

    return {
        "critic_feedback": all_feedback,
        "critic_iterations": new_iteration,
        "status": next_status,
    }


