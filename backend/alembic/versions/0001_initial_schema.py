"""Initial schema — all Eventura AI tables + pgvector extension.

Revision ID: 0001
Revises:
Create Date: 2026-09-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── vendors ──────────────────────────────────────────────────────────────
    op.create_table(
        "vendors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("event_types", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("base_price", sa.Float(), nullable=False),
        sa.Column("price_per_guest", sa.Float(), nullable=True),
        sa.Column("price_floor", sa.Float(), nullable=False),
        sa.Column("min_capacity", sa.Integer(), nullable=True),
        sa.Column("max_capacity", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), server_default="4.0"),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("min_notice_days", sa.Integer(), server_default="7"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_synthetic", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── vendor_availability ───────────────────────────────────────────────────
    op.create_table(
        "vendor_availability",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_id",
            sa.String(36),
            sa.ForeignKey("vendors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default="true"),
        sa.Column("booked_by_session", sa.String(36), nullable=True),
        sa.UniqueConstraint("vendor_id", "date", name="uq_vendor_date"),
    )

    # ── knowledge_chunks ──────────────────────────────────────────────────────
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(100), nullable=False),
        sa.Column("document_title", sa.String(255), nullable=False),
        sa.Column("event_types", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── sessions ──────────────────────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), server_default="created"),
        sa.Column("rag_mode", sa.String(20), server_default="agentic"),
        sa.Column("llm_provider", sa.String(30), server_default="gemini"),
        sa.Column("state_snapshot", sa.JSON(), nullable=True),
        sa.Column("critic_iterations", sa.Integer(), server_default="0"),
        sa.Column("retrieval_rounds", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── event_log ─────────────────────────────────────────────────────────────
    op.create_table(
        "event_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="success"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── bookings ──────────────────────────────────────────────────────────────
    op.create_table(
        "bookings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            sa.String(36),
            sa.ForeignKey("vendors.id"),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("quoted_price", sa.Float(), nullable=False),
        sa.Column("final_price", sa.Float(), nullable=True),
        sa.Column("hold_reference", sa.String(100), nullable=True),
        sa.Column("confirmation_reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── guests ────────────────────────────────────────────────────────────────
    op.create_table(
        "guests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("consent", sa.Boolean(), server_default="false"),
        sa.Column("invite_status", sa.String(50), server_default="pending"),
    )

    # ── messages ──────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── reminders ─────────────────────────────────────────────────────────────
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_template", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), server_default="scheduled"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved", sa.Boolean(), server_default="false"),
    )

    # ── eval_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scenario_id", sa.String(100), nullable=False),
        sa.Column("rag_mode", sa.String(20), nullable=False),
        sa.Column("llm_provider", sa.String(30), nullable=False),
        sa.Column("critic_enabled", sa.Boolean(), server_default="true"),
        sa.Column("run_index", sa.Integer(), server_default="0"),
        sa.Column("constraint_satisfaction", sa.Float(), nullable=True),
        sa.Column("budget_adherence", sa.Float(), nullable=True),
        sa.Column("evidence_grounding", sa.Float(), nullable=True),
        sa.Column("hallucination_rate", sa.Float(), nullable=True),
        sa.Column("task_completion", sa.Float(), nullable=True),
        sa.Column("infeasibility_detected", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("raw_result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # Indexes for common queries
    op.create_index("ix_vendors_city_category", "vendors", ["city", "category"])
    op.create_index("ix_vendors_event_types", "vendors", ["event_types"], postgresql_using="gin")
    op.create_index("ix_event_log_session", "event_log", ["session_id", "timestamp"])
    op.create_index("ix_knowledge_chunks_event_types", "knowledge_chunks", ["event_types"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("eval_runs")
    op.drop_table("reminders")
    op.drop_table("messages")
    op.drop_table("guests")
    op.drop_table("bookings")
    op.drop_table("event_log")
    op.drop_table("sessions")
    op.drop_table("knowledge_chunks")
    op.drop_table("vendor_availability")
    op.drop_table("vendors")
    op.execute("DROP EXTENSION IF EXISTS vector")
