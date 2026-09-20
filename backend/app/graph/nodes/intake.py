"""
Intake Agent — Eventura AI

Responsibilities:
  - Parse natural language event descriptions
  - Extract structured requirements using the LLM
  - Validate that all critical fields are present
  - Ask the user for missing critical information
  - Update existing requirements on follow-up messages (e.g. budget increase)

Critical fields: event_type, city, guest_count, budget, date
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.graph.activity import emit_activity
from app.graph.state import EventState, Requirements
from app.llm.base import get_llm
from app.logger import get_logger

logger = get_logger(__name__)

CRITICAL_FIELDS = ["event_type", "city", "guest_count", "budget", "date"]
VALID_EVENT_TYPES = {"wedding", "birthday", "college_fest"}

SYSTEM_PROMPT = """You are the Intake Agent for Eventura AI, an agentic event planning platform.

Your job is to extract structured event requirements from the user's message.

Extract the following fields (return JSON only, no explanation):
{
  "event_type": "wedding" | "birthday" | "college_fest" | null,
  "city": "string or null",
  "state": "string or null",
  "guest_count": integer or null,
  "budget": number in INR or null,
  "date": "YYYY-MM-DD" or null,
  "duration_days": integer or null,
  "preferences": {
    "themes": [],
    "cuisine": [],
    "style_keywords": [],
    "language": [],
    "notes": ""
  },
  "constraints": {
    "mandatory_categories": [],
    "excluded_vendors": [],
    "notes": ""
  },
  "is_update": false
}

Rules:
- If the user says "increase budget to X" or "change date to Y", set is_update=true
- Convert budget to float in INR (e.g. "15 lakh" → 1500000, "₹5L" → 500000)
- Convert dates to YYYY-MM-DD (e.g. "December 20" → use current year if unambiguous)
- For event_type: "Tamil wedding" → "wedding", "cultural fest" → "college_fest"
- Return null for any field not mentioned — do NOT guess
- Return only valid JSON, nothing else
"""


async def intake_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Intake Agent.
    Extracts or updates requirements from the latest user message.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")

    await emit_activity(
        session_id=session_id,
        agent="IntakeAgent",
        action="parse_requirements",
        status="running",
        detail="Parsing event description…",
        db=db,
    )

    # Get the latest human message
    messages = state.get("messages", [])
    latest_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            latest_msg = msg.get("content", "")
            break
        elif hasattr(msg, "content") and msg.__class__.__name__ == "HumanMessage":
            latest_msg = msg.content
            break

    if not latest_msg:
        return {
            "errors": state.get("errors", []) + ["IntakeAgent: No user message found"],
            "status": "failed",
        }

    # Call LLM to extract structured requirements
    llm = get_llm(provider=state.get("llm_provider"), temperature=0.0)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=latest_msg),
        ])

        raw = response.content.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        extracted = json.loads(raw)
    except Exception as e:
        logger.warning("IntakeAgent LLM extraction failed", error=str(e))
        extracted = {}

    # Merge with existing requirements (handle updates)
    existing = dict(state.get("requirements", {}))
    is_update = extracted.pop("is_update", False)

    new_req = _merge_requirements(existing, extracted, is_update)

    # Normalise values
    new_req = _normalise_requirements(new_req)

    # Check which critical fields are still missing
    missing = [f for f in CRITICAL_FIELDS if not new_req.get(f)]

    requirements_complete = len(missing) == 0

    # Build assistant response
    if requirements_complete:
        assistant_msg = _confirm_message(new_req)
        status = "planning" if not is_update else state.get("status", "planning")
    else:
        assistant_msg = _ask_for_missing(missing, new_req)
        status = "needs_info"

    await emit_activity(
        session_id=session_id,
        agent="IntakeAgent",
        action="extract_requirements",
        status="success",
        detail=(
            f"Extracted: event={new_req.get('event_type')}, "
            f"city={new_req.get('city')}, "
            f"guests={new_req.get('guest_count')}, "
            f"budget=₹{new_req.get('budget', 0):,.0f}"
            + (f" | Missing: {', '.join(missing)}" if missing else "")
        ),
        db=db,
    )

    updates: dict = {
        "requirements": new_req,
        "requirements_complete": requirements_complete,
        "missing_fields": missing,
        "status": status,
        "messages": [{"role": "assistant", "content": assistant_msg}],
    }

    # If this is a budget/date update, signal the graph to continue
    if is_update and requirements_complete:
        updates["status"] = "replanning"

    return updates


def _merge_requirements(
    existing: dict,
    extracted: dict,
    is_update: bool,
) -> dict:
    """Merge newly extracted fields into existing requirements."""
    merged = dict(existing)
    for key, value in extracted.items():
        if value is not None:
            if key == "preferences" and isinstance(value, dict):
                old_prefs = merged.get("preferences", {})
                merged["preferences"] = {**old_prefs, **{k: v for k, v in value.items() if v}}
            elif key == "constraints" and isinstance(value, dict):
                old_const = merged.get("constraints", {})
                merged["constraints"] = {**old_const, **{k: v for k, v in value.items() if v}}
            else:
                merged[key] = value
    return merged


def _normalise_requirements(req: dict) -> dict:
    """Clean up and normalise extracted values."""
    # Normalise event_type
    et = req.get("event_type", "")
    if isinstance(et, str):
        et = et.lower().strip().replace(" ", "_")
        if et not in VALID_EVENT_TYPES:
            req.pop("event_type", None)
        else:
            req["event_type"] = et

    # Ensure guest_count is an int
    gc = req.get("guest_count")
    if gc is not None:
        try:
            req["guest_count"] = int(gc)
        except (TypeError, ValueError):
            req.pop("guest_count", None)

    # Ensure budget is a float
    budget = req.get("budget")
    if budget is not None:
        try:
            req["budget"] = float(budget)
        except (TypeError, ValueError):
            req.pop("budget", None)

    # Ensure duration_days has a default
    if not req.get("duration_days"):
        req["duration_days"] = 1

    return req


def _confirm_message(req: dict) -> str:
    """Build a confirmation message once all requirements are captured."""
    et = req.get("event_type", "").replace("_", " ").title()
    city = req.get("city", "")
    guests = req.get("guest_count", 0)
    budget = req.get("budget", 0)
    date = req.get("date", "")
    days = req.get("duration_days", 1)
    themes = req.get("preferences", {}).get("themes", [])
    theme_str = f" ({', '.join(themes)})" if themes else ""

    return (
        f"Got it! Planning a {et}{theme_str} in {city} for {guests:,} guests "
        f"with a budget of ₹{budget:,.0f} on {date} "
        f"({'2 days' if days == 2 else f'{days} day'}).\n\n"
        f"Starting the AI planning agents now…"
    )


def _ask_for_missing(missing: list[str], req: dict) -> str:
    """Build a targeted question for missing critical fields."""
    field_labels = {
        "event_type": "the type of event (Wedding, Birthday, or College Fest)",
        "city": "the city where the event will be held",
        "guest_count": "the expected number of guests",
        "budget": "your total budget (in INR)",
        "date": "the event date",
    }
    questions = [field_labels.get(f, f) for f in missing]
    if len(questions) == 1:
        return f"Could you tell me {questions[0]}?"
    return (
        "To complete your event plan, I need a few more details:\n"
        + "\n".join(f"• {q}" for q in questions)
    )


