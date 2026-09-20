"""
Pydantic request/response schemas for the Eventura AI REST API.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Session ───────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Natural language event description")
    rag_mode: Literal["none", "basic", "agentic"] = "agentic"
    llm_provider: Literal["gemini", "groq", "ollama"] = "gemini"


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class SessionOut(BaseModel):
    id: str
    event_type: str | None
    status: str
    rag_mode: str
    llm_provider: str
    created_at: str
    updated_at: str
    requirements: dict | None = None
    feasibility: dict | None = None
    vendor_selections: list[dict] = []
    budget_summary: dict | None = None
    negotiation_logs: list[dict] = []
    critic_feedback: list[dict] = []
    bookings: list[dict] = []
    run_of_show: list[dict] | None = None
    evidence_count: int = 0
    retrieval_rounds: int = 0
    critic_iterations: int = 0
    awaiting_human: bool = False
    hitl_gate: str | None = None
    errors: list[str] = []
    synthetic_disclaimer: str = (
        "Demo vendor and pricing data are synthetic and used for "
        "demonstration purposes only."
    )


class SessionListOut(BaseModel):
    sessions: list[SessionOut]
    total: int


# ── Approval / HITL ───────────────────────────────────────────────────────────

class ApprovalPayloadOut(BaseModel):
    """What the frontend shows to the human reviewer."""
    hitl_gate: str
    session_id: str
    payload: dict
    status: str = "pending"


class ApproveRequest(BaseModel):
    action: Literal["approve", "modify", "reject_vendor"] = "approve"
    message: str = ""
    rejected_vendor_ids: list[str] = []
    modifications: dict = {}


class ApproveResponse(BaseModel):
    session_id: str
    action: str
    status: str
    message: str = ""


# ── Disruption ────────────────────────────────────────────────────────────────

class DisruptRequest(BaseModel):
    disruption_type: Literal["vendor_cancelled", "budget_reduced"]
    vendor_id: str | None = None          # for vendor_cancelled
    reduction_pct: float | None = None    # for budget_reduced (e.g. 15.0)
    reason: str = ""


class DisruptResponse(BaseModel):
    session_id: str
    disruption_type: str
    affected_categories: list[str]
    before_budget: float | None = None
    after_budget: float | None = None
    message: str


# ── Mood board ────────────────────────────────────────────────────────────────

class MoodBoardResponse(BaseModel):
    session_id: str
    theme: str
    colors: list[str]
    style_keywords: list[str]


# ── Guests ────────────────────────────────────────────────────────────────────

class GuestIn(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    consent: bool = False


class GuestOut(BaseModel):
    id: str
    name: str
    phone: str | None
    email: str | None
    consent: bool
    invite_status: str


class GuestUploadResponse(BaseModel):
    session_id: str
    total_uploaded: int
    consented: int
    excluded_no_consent: int
    guests: list[GuestOut]


# ── Invitation ────────────────────────────────────────────────────────────────

class InvitePreviewRequest(BaseModel):
    language: Literal["english", "tamil", "both"] = "english"
    tone: str = "formal"
    custom_message: str = ""


class InvitePreviewResponse(BaseModel):
    session_id: str
    invite_text: str
    html_preview_url: str | None
    language: str
    tone: str


class InviteSendRequest(BaseModel):
    confirmed: bool = True  # must be explicitly true


class InviteSendResponse(BaseModel):
    session_id: str
    total_sent: int
    failed: int
    status: str


# ── Reminders ─────────────────────────────────────────────────────────────────

class ReminderApproveRequest(BaseModel):
    approved: bool = True
    schedule: list[dict] = []


class ReminderApproveResponse(BaseModel):
    session_id: str
    approved_count: int
    status: str


# ── Time simulation ───────────────────────────────────────────────────────────

class TimeAdvanceRequest(BaseModel):
    days: int = Field(..., gt=0, le=365)


# ── Evaluation ────────────────────────────────────────────────────────────────

class EvalRunRequest(BaseModel):
    scenario_ids: list[str] = []   # empty = run all scenarios
    rag_modes: list[str] = ["none", "basic", "agentic"]
    llm_providers: list[str] = ["gemini"]
    critic_enabled_values: list[bool] = [True, False]
    runs_per_scenario: int = Field(default=3, ge=1, le=5)


class EvalRunResponse(BaseModel):
    run_id: str
    scenarios_queued: int
    estimated_duration_minutes: float
    status: str = "started"


class EvalResultsOut(BaseModel):
    runs: list[dict]
    summary: dict
    generated_at: str


# ── Activity events (SSE payload) ─────────────────────────────────────────────

class ActivityEventOut(BaseModel):
    id: str
    session_id: str
    agent: str
    action: str
    status: str
    detail: str | None
    payload: dict | None
    timestamp: str
