"""
Unified retrieval interface for Eventura AI agents.

Agents call retrieve() with a mode and information need.
The mode is pulled from the session state so it applies consistently
across all retrieval calls in a session.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.retrieval.evidence import Evidence
from app.retrieval.rag_modes import (
    RetrievalResult,
    retrieve_agentic,
    retrieve_basic,
    retrieve_none,
)

logger = get_logger(__name__)

RagMode = Literal["none", "basic", "agentic"]


async def retrieve(
    db: AsyncSession,
    session_id: str,
    rag_mode: RagMode,
    requirements: dict,
    information_need: dict,
    retrieval_round: int = 0,
    existing_evidence: list[Evidence] | None = None,
    llm: Any = None,
    rejected_vendor_ids: list[str] | None = None,
) -> RetrievalResult:
    """
    Dispatch to the appropriate retrieval mode.

    Parameters
    ----------
    db:
        Async SQLAlchemy session.
    session_id:
        Session identifier for evidence scoping and logging.
    rag_mode:
        "none" | "basic" | "agentic"
    requirements:
        Structured event requirements from the Intake Agent.
    information_need:
        What the Planner Agent needs for a specific category.
        {"category": "venue", "description": "...", "constraints": {...}}
    retrieval_round:
        Current round (0 = initial, 1-2 = re-retrieval).
    existing_evidence:
        Evidence from previous rounds to avoid duplication.
    llm:
        LangChain LLM instance (only used by agentic mode for query rewriting
        if enabled in future — currently queries are constructed deterministically).
    """
    logger.info(
        "Retrieval dispatch",
        session_id=session_id,
        mode=rag_mode,
        category=information_need.get("category"),
        round=retrieval_round,
    )

    if rag_mode == "none":
        return await retrieve_none(session_id=session_id, requirements=requirements)

    elif rag_mode == "basic":
        return await retrieve_basic(
            db=db,
            session_id=session_id,
            requirements=requirements,
            information_need=information_need,
        )

    elif rag_mode == "agentic":
        return await retrieve_agentic(
            db=db,
            session_id=session_id,
            requirements=requirements,
            information_need=information_need,
            retrieval_round=retrieval_round,
            existing_evidence=existing_evidence,
            llm=llm,
            rejected_vendor_ids=rejected_vendor_ids,
        )

    else:
        raise ValueError(f"Unknown RAG mode: {rag_mode!r}")


def build_information_need(
    category: str,
    event_type: str,
    city: str,
    description: str = "",
    constraints: dict | None = None,
) -> dict:
    """
    Helper to construct a well-formed information_need dict.
    Used by the Planner Agent when decomposing an event into categories.
    """
    return {
        "category": category,
        "event_type": event_type,
        "city": city,
        "description": description or f"{event_type} {category} in {city}",
        "constraints": constraints or {},
    }
