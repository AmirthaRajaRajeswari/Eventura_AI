"""
Budget Agent — Eventura AI

FULLY DETERMINISTIC. No LLM arithmetic.

Responsibilities:
  - Calculate total cost from selected vendors
  - Compare against budget allocation per category
  - Identify over-budget categories
  - Calculate negotiation savings
  - Update budget summary in state
"""

from __future__ import annotations

from app.graph.activity import emit_activity
from app.graph.state import EventState
from app.logger import get_logger
from app.retrieval.feasibility import calculate_remaining_budget

logger = get_logger(__name__)


async def budget_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Budget Agent.
    All arithmetic is deterministic Python — never delegated to LLM.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")
    req = state.get("requirements", {})
    total_budget = req.get("budget", 0.0)
    vendor_selections = state.get("vendor_selections", [])
    budget_breakdown = state.get("budget_breakdown", {})

    await emit_activity(
        session_id=session_id,
        agent="BudgetAgent",
        action="calculate_budget",
        status="running",
        detail=f"Calculating costs for {len(vendor_selections)} vendor selections…",
        db=db,
    )

    # ── Build category actuals from selected vendors ───────────────────────
    category_actuals: dict[str, float] = {}
    over_budget_categories: list[str] = []

    for sel in vendor_selections:
        category = sel.get("category", "")
        # Use final_price if negotiated, else quoted_price
        price = sel.get("final_price") or sel.get("quoted_price", 0.0)
        category_actuals[category] = round(price, 2)

        # Check against allocation
        allocated = budget_breakdown.get(category, 0.0)
        if allocated > 0 and price > allocated * 1.15:  # 15% tolerance
            over_budget_categories.append(category)

    # ── Deterministic budget summary ──────────────────────────────────────
    budget_summary = calculate_remaining_budget(
        total_budget=total_budget,
        category_costs=category_actuals,
    )

    # ── Negotiation savings summary ───────────────────────────────────────
    total_savings = sum(
        sel.get("negotiation_savings", 0.0) for sel in vendor_selections
    )
    budget_summary["negotiation_savings"] = round(total_savings, 2)
    budget_summary["over_budget_categories"] = over_budget_categories

    detail = (
        f"Total: ₹{budget_summary['spent']:,.0f} / ₹{total_budget:,.0f} "
        f"({budget_summary['pct_used']:.1f}% used) | "
        f"Remaining: ₹{budget_summary['remaining']:,.0f}"
        + (f" | OVER BUDGET: {over_budget_categories}" if over_budget_categories else "")
        + (f" | Savings: ₹{total_savings:,.0f}" if total_savings > 0 else "")
    )

    await emit_activity(
        session_id=session_id,
        agent="BudgetAgent",
        action="calculate_budget",
        status="success" if not budget_summary["over_budget"] else "warning",
        detail=detail,
        payload=budget_summary,
        db=db,
    )

    # ── Update vendor selections with final pricing notes ─────────────────
    updated_selections = []
    for sel in vendor_selections:
        updated_sel = dict(sel)
        cat = sel.get("category", "")
        allocated = budget_breakdown.get(cat, 0.0)
        actual = category_actuals.get(cat, 0.0)
        if allocated > 0 and actual > allocated * 1.15:
            warnings = list(sel.get("critic_warnings", []))
            warnings.append(
                f"Over allocated budget: ₹{actual:,.0f} vs ₹{allocated:,.0f} allocated"
            )
            updated_sel["critic_warnings"] = warnings
        updated_selections.append(updated_sel)

    return {
        "category_actuals": category_actuals,
        "budget_summary": budget_summary,
        "vendor_selections": updated_selections,
        "status": "negotiating",
    }


