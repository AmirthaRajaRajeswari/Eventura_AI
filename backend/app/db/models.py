"""
SQLAlchemy ORM models for Eventura AI.

All tables are defined here and imported by Alembic's env.py.

NOTE: The pgvector extension must be enabled in PostgreSQL before running
migrations:  CREATE EXTENSION IF NOT EXISTS vector;
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Vendors ───────────────────────────────────────────────────────────────────

class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    event_types: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=True)

    # Pricing (INR)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_guest: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_floor: Mapped[float] = mapped_column(Float, nullable=False)  # hidden minimum
    min_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metadata
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=True)
    min_notice_days: Mapped[int] = mapped_column(Integer, default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    availability: Mapped[list["VendorAvailability"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="vendor")


class VendorAvailability(Base):
    __tablename__ = "vendor_availability"
    __table_args__ = (
        UniqueConstraint("vendor_id", "date", name="uq_vendor_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    booked_by_session: Mapped[str | None] = mapped_column(String(36), nullable=True)

    vendor: Mapped["Vendor"] = relationship(back_populates="availability")


# ── Knowledge base ────────────────────────────────────────────────────────────

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(100), nullable=False)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_types: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=True, default=dict)

    # pgvector embedding (384-dim for all-MiniLM-L6-v2)
    embedding: Mapped[Any] = mapped_column(Vector(384), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── Sessions ──────────────────────────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created")
    rag_mode: Mapped[str] = mapped_column(String(20), default="agentic")
    llm_provider: Mapped[str] = mapped_column(String(30), default="gemini")

    # Full LangGraph state snapshot
    state_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Critic / planner iteration counters
    critic_iterations: Mapped[int] = mapped_column(Integer, default=0)
    retrieval_rounds: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    event_logs: Mapped[list["EventLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="session")
    guests: Mapped[list["Guest"]] = relationship(back_populates="session")
    messages: Mapped[list["Message"]] = relationship(back_populates="session")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="session")


class EventLog(Base):
    """Fine-grained agent activity log — feeds the SSE activity feed."""
    __tablename__ = "event_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    agent: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["Session"] = relationship(back_populates="event_logs")


# ── Bookings ──────────────────────────────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # hold/confirmed/cancelled
    quoted_price: Mapped[float] = mapped_column(Float, nullable=False)
    final_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    hold_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmation_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["Session"] = relationship(back_populates="bookings")
    vendor: Mapped["Vendor"] = relationship(back_populates="bookings")


# ── Guests ────────────────────────────────────────────────────────────────────

class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    invite_status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending | sent | delivered | failed

    session: Mapped["Session"] = relationship(back_populates="guests")


# ── Messages ──────────────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["Session"] = relationship(back_populates="messages")


# ── Reminders ─────────────────────────────────────────────────────────────────

class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "7_days_before", "1_day_before", "day_of"
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    # scheduled | sent | failed | cancelled
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["Session"] = relationship(back_populates="reminders")


# ── Evaluation runs ───────────────────────────────────────────────────────────

class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rag_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(30), nullable=False)
    critic_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    run_index: Mapped[int] = mapped_column(Integer, default=0)

    # Metrics
    constraint_satisfaction: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_adherence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_grounding: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    task_completion: Mapped[float | None] = mapped_column(Float, nullable=True)
    infeasibility_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
