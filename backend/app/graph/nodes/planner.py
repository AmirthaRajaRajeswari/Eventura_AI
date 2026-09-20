"""
Planner Agent — Eventura AI (Supervisor)

Responsibilities:
  - Decompose the event into planning categories
  - Generate information needs for the Research Agent
  - Incorporate human feedback and re-plan
  - Decide which categories need replanning after disruption
  - Produce a structured plan from Research + Budget results
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.activity import emit_activity
from app.graph.state import EventState
from app.llm.base import get_llm
from app.logger import get_logger
from app.retrieval.feasibility import (
    MANDATORY_CATEGORIES,
    OPTIONAL_CATEGORIES,
    calculate_budget_breakdown,
)

logger = get_logger(__name__)

PLANNER_SYSTEM = """You are the Planner Agent for Eventura AI.

Given event requirements and a budget breakdown, create information needs
for each vendor category that the Research Agent will use to find vendors.

Return JSON array only:
[
  {
    "category": "venue",
    "description": "Wedding venue in Chennai for 500 guests",
    "constraints": {
      "min_capacity": 500,
      "max_price": 480000,
      "city": "Chennai",
      "date": "2026-12-20",
      "tags": ["AC", "stage", "parking"]
    },
    "priority": "mandatory"
  }
]

Rules:
- Include ALL mandatory categories first, then optional ones within budget
- Set priority: "mandatory" or "optional"
- Keep constraints concrete and numeric where possible
- Return only valid JSON, nothing else
"""


async def planner_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Planner Agent.
    Decomposes event into information needs per category.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")
    req = state.get("requirements", {})

    # Check if this is a replan after disruption
    is_disruption_replan = bool(state.get("disruption_type"))
    replan_categories = state.get("replan_categories", [])

    await emit_activity(
        session_id=session_id,
        agent="PlannerAgent",
        action="decompose_event",
        status="running",
        detail=(
            f"Decomposing {req.get('event_type', 'event')} planning into categories…"
            if not is_disruption_replan
            else f"Replanning categories: {replan_categories}"
        ),
        db=db,
    )

    event_type = req.get("event_type", "wedding")
    budget = req.get("budget", 0.0)
    guest_count = req.get("guest_count", 100)
    city = req.get("city", "")
    date_str = req.get("date")
    duration_days = req.get("duration_days", 1)

    # ── Deterministic budget allocation ───────────────────────────────────
    budget_breakdown = calculate_budget_breakdown(
        budget=budget,
        event_type=event_type,
        guest_count=guest_count,
        duration_days=duration_days,
    )

    # ── Determine categories to plan ──────────────────────────────────────
    mandatory = MANDATORY_CATEGORIES.get(event_type, ["venue", "catering"])
    optional = OPTIONAL_CATEGORIES.get(event_type, [])

    if is_disruption_replan and replan_categories:
        # Only replan affected categories
        categories_to_plan = replan_categories
    else:
        categories_to_plan = mandatory + optional

    # ── LLM generates information needs ──────────────────────────────────
    user_prompt = _build_planner_prompt(
        req=req,
        budget_breakdown=budget_breakdown,
        categories=categories_to_plan,
        mandatory=mandatory,
        rejected_ids=state.get("rejected_vendor_ids", []),
        human_feedback=state.get("human_feedback", []),
    )

    information_needs = await _generate_information_needs(
        user_prompt=user_prompt,
        llm_provider=state.get("llm_provider"),
        fallback_categories=categories_to_plan,
        req=req,
        budget_breakdown=budget_breakdown,
        mandatory=mandatory,
    )

    await emit_activity(
        session_id=session_id,
        agent="PlannerAgent",
        action="decompose_event",
        status="success",
        detail=(
            f"Created {len(information_needs)} information needs "
            f"({len([n for n in information_needs if n.get('priority')=='mandatory'])} mandatory)"
        ),
        db=db,
    )

    updates: dict = {
        "information_needs": information_needs,
        "budget_breakdown": budget_breakdown,
        "status": "researching",
    }

    # Reset critic iterations for fresh planning
    if not is_disruption_replan:
        updates["critic_iterations"] = 0
        updates["vendor_selections"] = []
        updates["evidence"] = []
        updates["retrieval_rounds"] = 0

    return updates


def _build_planner_prompt(
    req: dict,
    budget_breakdown: dict,
    categories: list[str],
    mandatory: list[str],
    rejected_ids: list[str],
    human_feedback: list[dict],
) -> str:
    event_type = req.get("event_type", "wedding")
    city = req.get("city", "")
    guests = req.get("guest_count", 100)
    budget = req.get("budget", 0)
    date = req.get("date", "")
    prefs = req.get("preferences", {})
    themes = prefs.get("themes", [])

    feedback_note = ""
    if human_feedback:
        last_fb = human_feedback[-1]
        if last_fb.get("message"):
            feedback_note = f"\nHuman feedback: {last_fb['message']}"

    rejected_note = ""
    if rejected_ids:
        rejected_note = f"\nExclude vendors with IDs: {rejected_ids}"

    return f"""Event: {event_type.replace('_', ' ').title()} in {city}
Guests: {guests:,}
Budget: ₹{budget:,.0f}
Date: {date}
Themes/preferences: {', '.join(themes) if themes else 'not specified'}
Categories to plan: {', '.join(categories)}
Mandatory: {', '.join(mandatory)}
Budget allocation: {json.dumps({k: f'INR{v:,.0f}' for k, v in budget_breakdown.items()}, ensure_ascii=False)}
{feedback_note}{rejected_note}

Generate information needs for each category listed above."""


async def _generate_information_needs(
    user_prompt: str,
    llm_provider: str | None,
    fallback_categories: list[str],
    req: dict,
    budget_breakdown: dict,
    mandatory: list[str],
) -> list[dict]:
    """Use LLM to generate information needs; fall back to deterministic if LLM fails."""
    try:
        llm = get_llm(provider=llm_provider, temperature=0.1)
        resp = await llm.ainvoke([
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=user_prompt),
        ])
        raw = resp.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        needs = json.loads(raw)
        if isinstance(needs, list) and len(needs) > 0:
            return needs
    except Exception as e:
        logger.warning("PlannerAgent LLM failed, using fallback", error=str(e))

    # Deterministic fallback — always works
    return _deterministic_information_needs(
        categories=fallback_categories,
        req=req,
        budget_breakdown=budget_breakdown,
        mandatory=mandatory,
    )


def _deterministic_information_needs(
    categories: list[str],
    req: dict,
    budget_breakdown: dict,
    mandatory: list[str],
) -> list[dict]:
    """
    Build information needs deterministically without LLM.
    Used as fallback and in evaluation runs without API keys.
    """
    city = req.get("city", "")
    event_type = req.get("event_type", "wedding")
    guests = req.get("guest_count", 100)
    date = req.get("date", "")
    themes = req.get("preferences", {}).get("themes", [])

    needs = []
    for cat in categories:
        alloc = budget_breakdown.get(cat, 0)
        constraints: dict = {
            "city": city,
            "max_price": alloc * 1.2 if alloc else None,
        }
        if date:
            constraints["date"] = date
        if cat in ("venue", "catering"):
            constraints["min_capacity"] = guests
        if themes:
            constraints["tags"] = themes

        description = (
            f"{event_type.replace('_', ' ').title()} {cat} in {city}"
            + (f" for {guests:,} guests" if cat in ("venue", "catering") else "")
            + (f" on {date}" if date else "")
        )

        needs.append({
            "category": cat,
            "description": description,
            "constraints": {k: v for k, v in constraints.items() if v},
            "priority": "mandatory" if cat in mandatory else "optional",
        })

    return needs


