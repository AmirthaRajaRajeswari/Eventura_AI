"""
Human-in-the-Loop gate — Eventura AI

Implements LangGraph interrupt() for HITL pauses.

HITL Gate #1 — Plan Approval:
  User sees the full plan and can:
  - Approve → proceed to booking
  - Modify → send feedback back to Planner
  - Reject vendor → add to rejected list, re-plan that category

HITL Gate #2 — Invitation Approval:
  User sees invitation previews and can:
  - Approve → send invitations
  - Edit → regenerate with feedback

Irreversible actions (confirm_booking, send_invitations) CANNOT happen
without explicit human approval.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.graph.activity import emit_activity
from app.graph.state import EventState, HumanFeedback
from app.logger import get_logger

logger = get_logger(__name__)


async def human_review_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Human Review (HITL Gate #1 — Plan Approval).

    Uses LangGraph interrupt() to pause execution and wait for human input.
    The graph resumes when the human provides feedback via the approval API.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")

    await emit_activity(
        session_id=session_id,
        agent="System",
        action="await_human_approval",
        status="waiting",
        detail="Waiting for human plan approval… (approve / modify / reject vendor)",
        db=db,
    )

    # Build the approval payload shown to the user
    approval_payload = _build_approval_payload(state)

    # LangGraph interrupt — pauses graph execution here
    # The value passed to interrupt() is available to the frontend via the approval API
    human_input = interrupt({
        "hitl_gate": "plan_approval",
        "session_id": session_id,
        "payload": approval_payload,
    })

    # ── Resume: process human feedback ───────────────────────────────────
    # human_input is what was passed to Command(resume=...) by the approval endpoint
    action = human_input.get("action", "approve")
    message = human_input.get("message", "")
    rejected_vendor_ids = human_input.get("rejected_vendor_ids", [])
    modifications = human_input.get("modifications", {})

    feedback = HumanFeedback(
        action=action,
        message=message,
        rejected_vendor_ids=rejected_vendor_ids,
        modifications=modifications,
        timestamp=_now_iso(),
    )

    all_feedback = list(state.get("human_feedback", []))
    all_feedback.append(feedback)

    # Update rejected vendor list
    all_rejected = list(state.get("rejected_vendor_ids", []))
    all_rejected.extend(rejected_vendor_ids)
    all_rejected = list(set(all_rejected))

    await emit_activity(
        session_id=session_id,
        agent="System",
        action="human_feedback_received",
        status="success",
        detail=f"Human action: {action}" + (f" — {message}" if message else ""),
        db=db,
    )

    if action == "approve":
        return {
            "human_feedback": all_feedback,
            "rejected_vendor_ids": all_rejected,
            "awaiting_human": False,
            "hitl_gate": None,
            "status": "booking",
        }

    elif action == "modify":
        # Update requirements if modifications provided
        updates: dict = {
        "human_feedback": all_feedback,
        "rejected_vendor_ids": all_rejected,
        "awaiting_human": False,
        "hitl_gate": None,
        "status": "replanning",
        "critic_iterations": 0,
        }
        if modifications.get("budget"):
            req = dict(state.get("requirements", {}))
            req["budget"] = float(modifications["budget"])
            updates["requirements"] = req
            updates["feasibility"] = {}
        return updates

    elif action == "reject_vendor":
        # Remove rejected vendors from selections and re-plan those categories
        vendor_selections = list(state.get("vendor_selections", []))
        replan_categories = []
        for vid in rejected_vendor_ids:
            for sel in vendor_selections:
                if sel.get("vendor_id") == vid:
                    replan_categories.append(sel.get("category"))
        return {
        "human_feedback": all_feedback,
        "rejected_vendor_ids": all_rejected,
        "awaiting_human": False,
        "hitl_gate": None,
        "status": "replanning",
        "replan_categories": list(set(replan_categories)),
        "critic_iterations": 0,
        }

    # Default: treat unknown actions as approve
    return {
        "human_feedback": all_feedback,
        "rejected_vendor_ids": all_rejected,
        "awaiting_human": False,
        "hitl_gate": None,
        "status": "booking",
    }


async def invite_review_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Invitation HITL Gate #2.
    Pauses before sending invitations.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")

    await emit_activity(
        session_id=session_id,
        agent="System",
        action="await_invite_approval",
        status="waiting",
        detail="Waiting for invitation approval before sending…",
        db=db,
    )

    human_input = interrupt({
        "hitl_gate": "invite_approval",
        "session_id": session_id,
        "payload": {
            "invite": state.get("invite"),
            "guests_count": len(state.get("guests", [])),
            "consented_count": sum(
                1 for g in state.get("guests", []) if g.get("consent")
            ),
        },
    })

    action = human_input.get("action", "approve")

    await emit_activity(
        session_id=session_id,
        agent="System",
        action="invite_feedback_received",
        status="success",
        detail=f"Invitation approval: {action}",
        db=db,
    )

    if action == "approve":
        invite = dict(state.get("invite") or {})
        invite["approved"] = True
        return {
            "invite": invite,
            "awaiting_human": False,
            "hitl_gate": None,
            "status": "sending_invites",
        }
    else:
        return {
            "awaiting_human": False,
            "hitl_gate": None,
            "status": "regenerate_invite",
        }


def _build_approval_payload(state: EventState) -> dict:
    """Build the structured plan payload shown to the human reviewer."""
    req = state.get("requirements", {})
    return {
        "requirements": {
            "event_type": req.get("event_type"),
            "city": req.get("city"),
            "guest_count": req.get("guest_count"),
            "budget": req.get("budget"),
            "date": req.get("date"),
            "duration_days": req.get("duration_days", 1),
        },
        "vendor_selections": state.get("vendor_selections", []),
        "budget_summary": state.get("budget_summary", {}),
        "negotiation_logs": state.get("negotiation_logs", []),
        "critic_feedback": state.get("critic_feedback", []),
        "evidence_count": len(state.get("evidence", [])),
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


