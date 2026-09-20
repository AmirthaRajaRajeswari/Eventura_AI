"""
LangGraph EventState for Eventura AI.

This is the single source of truth for the entire planning session.
It persists through HITL pauses, application restarts, and replanning.

Design principles:
  - Strongly typed (TypedDict + annotations)
  - Every agent reads from and writes to this state
  - No agent secretly mutates state outside the graph
  - Human feedback is first-class state, not an afterthought
"""

from __future__ import annotations

from typing import Annotated, Any
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class Requirements(TypedDict, total=False):
    event_type: str          # wedding | birthday | college_fest
    city: str
    state: str
    guest_count: int
    budget: float
    date: str                # YYYY-MM-DD
    duration_days: int
    preferences: dict        # themes, cuisine, style keywords, etc.
    constraints: dict        # hard constraints (e.g. must have traditional mandap)
    raw_prompt: str          # original user text


class FeasibilityState(TypedDict, total=False):
    feasible: bool
    min_cost: float
    shortfall: float
    coverage_pct: float
    issues: list[str]
    relaxations: list[str]
    category_min_costs: dict[str, float]
    warnings: list[str]
    checked: bool


class VendorSelection(TypedDict, total=False):
    vendor_id: str
    name: str
    category: str
    city: str
    base_price: float
    price_per_guest: float | None
    price_floor: float
    quoted_price: float
    final_price: float | None
    evidence_ids: list[str]
    negotiation_savings: float
    critic_warnings: list[str]
    status: str              # selected | approved | booked | rejected


class NegotiationRound(TypedDict, total=False):
    round_number: int
    our_offer: float
    vendor_response: str     # accepted | counter | rejected
    counter_price: float | None
    final_price: float | None
    message: str
    timestamp: str


class NegotiationLog(TypedDict, total=False):
    vendor_id: str
    category: str
    initial_price: float
    final_price: float | None
    savings: float
    rounds: list[NegotiationRound]
    status: str              # in_progress | accepted | rejected


class CriticIssue(TypedDict, total=False):
    type: str                # missing_evidence | budget_exceeded | capacity_mismatch | etc.
    severity: str            # high | medium | low
    category: str
    detail: str


class CriticFeedback(TypedDict, total=False):
    passed: bool
    issues: list[CriticIssue]
    iteration: int
    resolved: bool


class HumanFeedback(TypedDict, total=False):
    action: str              # approve | modify | reject_vendor | reject_all
    message: str
    rejected_vendor_ids: list[str]
    modifications: dict
    timestamp: str


class BookingRecord(TypedDict, total=False):
    vendor_id: str
    category: str
    status: str              # hold | confirmed | cancelled
    quoted_price: float
    final_price: float
    hold_reference: str
    confirmation_reference: str


class RunOfShowItem(TypedDict, total=False):
    activity: str
    start_time: str
    end_time: str
    duration_minutes: int
    owner: str
    description: str
    day: int


class InviteState(TypedDict, total=False):
    text: str
    language: str            # english | tamil | both
    tone: str
    theme: str
    html_path: str
    approved: bool
    send_status: str         # pending | approved | sent


class DeliveryRecord(TypedDict, total=False):
    guest_id: str
    guest_name: str
    channel: str
    status: str              # pending | sent | delivered | failed
    sent_at: str


class ReminderRecord(TypedDict, total=False):
    trigger_type: str
    scheduled_at: str
    message_template: str
    status: str
    approved: bool


class MoodBoardTheme(TypedDict, total=False):
    theme: str
    colors: list[str]
    style_keywords: list[str]
    source: str              # user_upload | generated


class EventState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────────────
    session_id: str
    llm_provider: str        # gemini | groq | ollama
    rag_mode: str            # none | basic | agentic
    status: str              # created | planning | awaiting_approval | approved |
                             # booking | completed | failed | disrupted

    # ── Conversation ──────────────────────────────────────────────────────
    messages: Annotated[list[dict], add_messages]

    # ── Requirements (set by IntakeAgent) ─────────────────────────────────
    requirements: Requirements
    requirements_complete: bool   # all critical fields present?
    missing_fields: list[str]

    # ── Mood board (optional) ─────────────────────────────────────────────
    mood_board: MoodBoardTheme | None

    # ── Feasibility (set by FeasibilityAgent) ─────────────────────────────
    feasibility: FeasibilityState

    # ── Planning ──────────────────────────────────────────────────────────
    information_needs: list[dict]     # what Planner says is needed per category
    vendor_selections: list[VendorSelection]
    rejected_vendor_ids: list[str]    # never re-select these

    # ── Retrieval evidence ────────────────────────────────────────────────
    evidence: list[dict]              # all EV-NNN records
    retrieval_rounds: int

    # ── Budget ────────────────────────────────────────────────────────────
    budget_breakdown: dict[str, float]     # recommended allocation per category
    category_actuals: dict[str, float]     # actual selected vendor prices
    budget_summary: dict                   # spent/remaining/pct

    # ── Negotiation ───────────────────────────────────────────────────────
    negotiation_logs: list[NegotiationLog]

    # ── Critic ────────────────────────────────────────────────────────────
    critic_feedback: list[CriticFeedback]
    critic_iterations: int            # max 2

    # ── Human-in-the-loop ─────────────────────────────────────────────────
    human_feedback: list[HumanFeedback]
    awaiting_human: bool
    hitl_gate: str | None             # "plan_approval" | "invite_approval"

    # ── Bookings ──────────────────────────────────────────────────────────
    bookings: list[BookingRecord]

    # ── Run-of-show ───────────────────────────────────────────────────────
    run_of_show: list[RunOfShowItem] | None

    # ── Invitations ───────────────────────────────────────────────────────
    invite: InviteState | None
    guests: list[dict]
    delivery_status: list[DeliveryRecord]

    # ── Reminders ─────────────────────────────────────────────────────────
    reminder_schedule: list[ReminderRecord]

    # ── Disruption tracking ───────────────────────────────────────────────
    disruption_type: str | None       # vendor_cancelled | budget_reduced
    disruption_detail: dict | None
    replan_categories: list[str]      # only replan these categories

    # ── Evaluation metadata ───────────────────────────────────────────────
    eval_metadata: dict | None        # token counts, latency, etc.

    # ── Error tracking ────────────────────────────────────────────────────
    errors: list[str]


def initial_state(
    session_id: str,
    rag_mode: str = "agentic",
    llm_provider: str = "gemini",
) -> EventState:
    """Return a clean initial state for a new session."""
    return EventState(
        session_id=session_id,
        llm_provider=llm_provider,
        rag_mode=rag_mode,
        status="created",
        messages=[],
        requirements={},
        requirements_complete=False,
        missing_fields=[],
        mood_board=None,
        feasibility={},
        information_needs=[],
        vendor_selections=[],
        rejected_vendor_ids=[],
        evidence=[],
        retrieval_rounds=0,
        budget_breakdown={},
        category_actuals={},
        budget_summary={},
        negotiation_logs=[],
        critic_feedback=[],
        critic_iterations=0,
        human_feedback=[],
        awaiting_human=False,
        hitl_gate=None,
        bookings=[],
        run_of_show=None,
        invite=None,
        guests=[],
        delivery_status=[],
        reminder_schedule=[],
        disruption_type=None,
        disruption_detail=None,
        replan_categories=[],
        eval_metadata=None,
        errors=[],
    )
