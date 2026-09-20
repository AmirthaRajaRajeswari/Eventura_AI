"""
Feasibility Agent — Eventura AI

MOSTLY DETERMINISTIC. The LLM only explains results it did not compute.

Responsibilities:
  - Calculate minimum possible cost from cheapest vendors
  - Check budget, capacity, date, mandatory categories
  - Return structured FeasibilityResult
  - Suggest concrete relaxations if infeasible
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.activity import emit_activity
from app.graph.state import EventState
from app.llm.base import get_llm
from app.logger import get_logger
from app.retrieval.feasibility import check_feasibility

logger = get_logger(__name__)


async def feasibility_node(state: EventState, config: RunnableConfig) -> dict:
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")
    req = state.get("requirements", {})

    await emit_activity(
        session_id=session_id,
        agent="FeasibilityAgent",
        action="check_feasibility",
        status="running",
        detail="Running deterministic feasibility checks…",
        db=db,
    )

    event_type = req.get("event_type", "wedding")
    city = req.get("city", "")
    guest_count = req.get("guest_count", 0)
    budget = req.get("budget", 0.0)
    date_str = req.get("date")
    duration_days = req.get("duration_days", 1)

    # ── Deterministic feasibility calculation ─────────────────────────────
    result = await check_feasibility(
        db=db,
        event_type=event_type,
        city=city,
        guest_count=guest_count,
        budget=budget,
        date_str=date_str,
        duration_days=duration_days,
    )

    feasibility_dict = result.to_dict()

    # ── LLM explains the deterministic result (does NOT compute it) ────────
    explanation = await _explain_feasibility(
        result=feasibility_dict,
        req=req,
        llm_provider=state.get("llm_provider"),
    )

    status_msg = "success" if result.feasible else "error"
    detail_msg = (
        f"Feasible ✓ (min cost ₹{result.min_cost:,.0f}, "
        f"budget ₹{budget:,.0f}, coverage {result.coverage_pct:.0f}%)"
        if result.feasible
        else (
            f"Infeasible ✗ — shortfall ₹{result.shortfall:,.0f} "
            f"(min ₹{result.min_cost:,.0f}, budget ₹{budget:,.0f})"
        )
    )

    await emit_activity(
        session_id=session_id,
        agent="FeasibilityAgent",
        action="check_feasibility",
        status=status_msg,
        detail=detail_msg,
        payload=feasibility_dict,
        db=db,
    )

    next_status = "planning" if result.feasible else "infeasible"

    return {
        "feasibility": {**feasibility_dict, "checked": True},
        "status": next_status,
        "messages": [{"role": "assistant", "content": explanation}],
    }


async def _explain_feasibility(
    result: dict,
    req: dict,
    llm_provider: str | None,
) -> str:
    """LLM explains the deterministic result — does NOT recalculate."""
    feasible = result.get("feasible", False)
    min_cost = result.get("min_cost", 0)
    budget = result.get("budget", 0)
    shortfall = result.get("shortfall", 0)
    issues = result.get("issues", [])
    relaxations = result.get("relaxations", [])
    category_costs = result.get("category_min_costs", {})

    if feasible:
        prompt = (
            f"The event is feasible. Minimum estimated cost is ₹{min_cost:,.0f} "
            f"against a budget of ₹{budget:,.0f} "
            f"(coverage: {result.get('coverage_pct', 0):.0f}%). "
            f"Category breakdown: {category_costs}. "
            "Write a brief 2-sentence confirmation for the user."
        )
    else:
        prompt = (
            f"The event is NOT feasible. Issues: {'; '.join(issues)}. "
            f"Minimum cost: ₹{min_cost:,.0f}, Budget: ₹{budget:,.0f}, "
            f"Shortfall: ₹{shortfall:,.0f}. "
            f"Suggested relaxations: {relaxations}. "
            "Write a brief, empathetic 3-sentence explanation for the user with the options."
        )

    try:
        llm = get_llm(provider=llm_provider, temperature=0.3)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return resp.content.strip()
    except Exception as e:
        logger.warning("FeasibilityAgent LLM explanation failed", error=str(e))
        if feasible:
            return (
                f"Your event is feasible. Estimated minimum cost is ₹{min_cost:,.0f} "
                f"within your budget of ₹{budget:,.0f}."
            )
        return (
            f"Your event may not be feasible within the current budget. "
            f"Minimum estimated cost is ₹{min_cost:,.0f} but budget is ₹{budget:,.0f} "
            f"(shortfall: ₹{shortfall:,.0f}). "
            + (f"Options: {'; '.join(relaxations[:2])}" if relaxations else "")
        )


