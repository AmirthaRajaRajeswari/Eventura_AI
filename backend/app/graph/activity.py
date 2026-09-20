"""
Agent activity emitter for Eventura AI.

Every agent node calls emit_activity() to push a structured event
into the per-session queue. The FastAPI SSE endpoint drains this queue
and streams events to the frontend in real time.

Events are also persisted to the event_log table.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from app.logger import get_logger

logger = get_logger(__name__)

# In-memory per-session event queues
# { session_id: asyncio.Queue }
_queues: dict[str, asyncio.Queue] = {}
_queue_lock = asyncio.Lock()


async def get_queue(session_id: str) -> asyncio.Queue:
    async with _queue_lock:
        if session_id not in _queues:
            _queues[session_id] = asyncio.Queue(maxsize=500)
        return _queues[session_id]


async def drop_queue(session_id: str) -> None:
    async with _queue_lock:
        _queues.pop(session_id, None)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def emit_activity(
    session_id: str,
    agent: str,
    action: str,
    status: str = "success",
    detail: str | None = None,
    payload: dict | None = None,
    db=None,  # optional AsyncSession for persistence
) -> dict:
    """
    Emit an agent activity event.

    Parameters
    ----------
    session_id : str
    agent      : e.g. "IntakeAgent", "ResearchAgent"
    action     : e.g. "extract_requirements", "retrieve_vendors"
    status     : "success" | "error" | "running" | "waiting"
    detail     : Human-readable description
    payload    : Optional structured data
    db         : If provided, persist to event_log table
    """
    event = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "agent": agent,
        "action": action,
        "status": status,
        "detail": detail,
        "payload": payload,
        "timestamp": _now_iso(),
    }

    logger.debug(
        "Agent activity",
        session_id=session_id,
        agent=agent,
        action=action,
        status=status,
    )

    # Push to SSE queue (non-blocking — drop if full)
    try:
        q = await get_queue(session_id)
        q.put_nowait(event)
    except asyncio.QueueFull:
        logger.warning("Activity queue full, dropping event", session_id=session_id)

    # Persist to DB if session available
    if db is not None:
        try:
            from app.db.models import EventLog
            log = EventLog(
                id=event["id"],
                session_id=session_id,
                agent=agent,
                action=action,
                status=status,
                detail=detail,
                payload=payload,
            )
            db.add(log)
            await db.flush()
        except Exception as e:
            logger.warning("Failed to persist activity event", error=str(e))

    return event
