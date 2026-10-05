"""

Session management API for Eventura AI.

Endpoints:

  POST /api/v1/sessions                — create session, start graph

  GET  /api/v1/sessions/{id}           — get session state

  GET  /api/v1/sessions                — list sessions

  POST /api/v1/sessions/{id}/message   — send follow-up message

  GET  /api/v1/sessions/{id}/stream    — SSE activity stream

  GET  /api/v1/sessions/{id}/approval  — get HITL approval payload

  POST /api/v1/sessions/{id}/approve   — submit human decision

  POST /api/v1/sessions/{id}/disrupt   — trigger disruption simulation

"""

from __future__ import annotations

import asyncio

import json

import uuid

from datetime import datetime, timezone

import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from langchain_core.runnables import RunnableConfig

from langgraph.types import Command

from sqlalchemy.ext.asyncio import AsyncSession

from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (

    ApprovalPayloadOut,

    ApproveRequest,

    ApproveResponse,

    CreateSessionRequest,

    DisruptRequest,

    DisruptResponse,

    SendMessageRequest,

    SessionListOut,

    SessionOut,

)

from app.db.models import Session as DBSession

from app.db.session import get_db

from app.graph.activity import drop_queue, emit_activity, get_queue

from app.graph.graph import get_graph

from app.graph.state import EventState, initial_state

from app.logger import get_logger

from app.retrieval.feasibility import apply_budget_reduction

from langchain_core.messages import BaseMessage

def _json_safe(value):

    """Convert LangGraph state into PostgreSQL JSON-safe data."""

    if value is None or isinstance(value, (str, int, float, bool)):

        return value

    # LangChain messages

    if isinstance(value, BaseMessage):

        return {

            "type": value.type,

            "content": _json_safe(value.content),

            "additional_kwargs": _json_safe(

                getattr(value, "additional_kwargs", {})

            ),

            "response_metadata": _json_safe(

                getattr(value, "response_metadata", {})

            ),

        }

    # Dictionaries

    if isinstance(value, dict):

        return {

            str(key): _json_safe(item)

            for key, item in value.items()

        }

    # Lists / tuples

    if isinstance(value, (list, tuple)):

        return [

            _json_safe(item)

            for item in value

        ]

    # Pydantic models

    if hasattr(value, "model_dump"):

        return _json_safe(value.model_dump())

    # Dates / datetimes

    if hasattr(value, "isoformat"):

        return value.isoformat()

    # Last resort

    return str(value)

router = APIRouter(prefix="/api/v1", tags=["sessions"])

logger = get_logger(__name__)

def _now_iso() -> str:

    return datetime.now(timezone.utc).isoformat()

def _thread_id(session_id: str) -> str:

    """LangGraph uses thread_id for checkpointing."""

    return session_id

# ── Create Session ────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionOut, status_code=201)

async def create_session(

    req: CreateSessionRequest,

    background_tasks: BackgroundTasks,

    db: AsyncSession = Depends(get_db),

) -> SessionOut:

    """

    Create a new planning session and start the agent graph in the background.

    Returns immediately with session ID — graph runs asynchronously.

    """

    session_id = str(uuid.uuid4())

    structlog.contextvars.bind_contextvars(session_id=session_id)

    logger.info(

        "Creating session",

        rag_mode=req.rag_mode,

        llm_provider=req.llm_provider,

    )

    # Persist session to DB

    db_session = DBSession(

        id=session_id,

        event_type=None,

        status="created",

        rag_mode=req.rag_mode,

        llm_provider=req.llm_provider,

    )

    db.add(db_session)

    await db.commit()

    # Build initial state with user message

    state = initial_state(

        session_id=session_id,

        rag_mode=req.rag_mode,

        llm_provider=req.llm_provider,

    )

    state["messages"] = [{"role": "user", "content": req.prompt}]

    # Start graph in background

    background_tasks.add_task(

        _run_graph_background,

        session_id=session_id,

        state=state,

        db_session_id=session_id,

    )

    return SessionOut(

        id=session_id,

        event_type=None,

        status="created",

        rag_mode=req.rag_mode,

        llm_provider=req.llm_provider,

        created_at=_now_iso(),

        updated_at=_now_iso(),

        awaiting_human=False,

    )

# ── Send Message ──────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/message", response_model=SessionOut)

async def send_message(

    session_id: str,

    req: SendMessageRequest,

    background_tasks: BackgroundTasks,

    db: AsyncSession = Depends(get_db),

) -> SessionOut:

    """

    Send a follow-up message to an existing session.

    Used when the Intake Agent asks for missing information.

    """

    db_session = await _get_db_session(session_id, db)

    structlog.contextvars.bind_contextvars(session_id=session_id)

    logger.info("Follow-up message received")

    # Get current graph state

    graph = get_graph()

    config = RunnableConfig(configurable={"thread_id": _thread_id(session_id), "db": None})

    values = db_session.state_snapshot or {}

    # Append the new user message and resume

        # Append the new user message and resume the graph

    new_message = {"role": "user", "content": req.message}

    updated_state = dict(values)

    updated_state["messages"] = (

        list(values.get("messages", [])) + [new_message]

    )

    background_tasks.add_task(

        _run_graph_background,

        session_id=session_id,

        state=updated_state,

        db_session_id=session_id,

    )

    db_session.status = "processing"

    await db.commit()

    # Refresh the ORM object before reading fields after commit.

    await db.refresh(db_session)

    return await _session_to_out(db_session, updated_state)

# ── Get Session ───────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}", response_model=SessionOut)

async def get_session(

    session_id: str,

    db: AsyncSession = Depends(get_db),

) -> SessionOut:

    db_session = await _get_db_session(session_id, db)

    # PostgreSQL is the durable source of truth for session state.

    values = db_session.state_snapshot or {}

    return await _session_to_out(db_session, values)

# ── List Sessions ─────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=SessionListOut)

async def list_sessions(

    db: AsyncSession = Depends(get_db),

) -> SessionListOut:

    from sqlalchemy import select

    result = await db.execute(

        select(DBSession).order_by(DBSession.created_at.desc()).limit(50)

    )

    sessions = result.scalars().all()

    out = []

    for s in sessions:

        out.append(SessionOut(

            id=s.id,

            event_type=s.event_type,

            status=s.status,

            rag_mode=s.rag_mode,

            llm_provider=s.llm_provider,

            created_at=s.created_at.isoformat() if s.created_at else _now_iso(),

            updated_at=s.updated_at.isoformat() if s.updated_at else _now_iso(),

        ))

    return SessionListOut(sessions=out, total=len(out))

# ── SSE Activity Stream ───────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/stream")

async def stream_activity(session_id: str) -> EventSourceResponse:

    """

    Server-Sent Events stream for live agent activity.

    The frontend connects here and receives events as agents work.

    """

    async def event_generator():

        q = await get_queue(session_id)

        # Send a connection confirmation

        yield {

            "event": "connected",

            "data": json.dumps({

                "session_id": session_id,

                "message": "Connected to activity stream",

            }),

        }

        # Stream events from the queue

        while True:

            try:

                event = await asyncio.wait_for(q.get(), timeout=30.0)

                yield {

                    "event": "activity",

                    "data": json.dumps(event),

                }

                q.task_done()

            except asyncio.TimeoutError:

                # Keep-alive ping

                yield {"event": "ping", "data": json.dumps({"ts": _now_iso()})}

            except Exception as e:

                logger.warning("SSE stream error", error=str(e))

                break

    return EventSourceResponse(event_generator())

# ── Approval (HITL) ───────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/approval", response_model=ApprovalPayloadOut)

async def get_approval(

    session_id: str,

    db: AsyncSession = Depends(get_db),

) -> ApprovalPayloadOut:

    """Get the current HITL approval payload for a session."""

    db_session = await _get_db_session(session_id, db)

    graph = get_graph()

    config = RunnableConfig(configurable={"thread_id": _thread_id(session_id), "db": None})

    try:

        state_snap = await graph.aget_state(config)

        values = state_snap.values if state_snap else {}

    except Exception:

        values = {}

    if not values.get("awaiting_human") and db_session.status not in ("awaiting_approval",):

        raise HTTPException(

            status_code=404,

            detail="No pending approval for this session",

        )

    from app.graph.nodes.human_review import _build_approval_payload

    payload = _build_approval_payload(values)  # type: ignore

    return ApprovalPayloadOut(

        hitl_gate=values.get("hitl_gate") or "plan_approval",

        session_id=session_id,

        payload=payload,

        status="pending",

    )

@router.post("/sessions/{session_id}/approve", response_model=ApproveResponse)

async def submit_approval(

    session_id: str,

    req: ApproveRequest,

    background_tasks: BackgroundTasks,

    db: AsyncSession = Depends(get_db),

) -> ApproveResponse:

    """

    Submit human approval/rejection/modification for a HITL gate.

    Resumes the paused LangGraph graph.

    """

    db_session = await _get_db_session(session_id, db)

    structlog.contextvars.bind_contextvars(session_id=session_id)

    logger.info("Human approval submitted", action=req.action)

    await emit_activity(

        session_id=session_id,

        agent="System",

        action="approval_submitted",

        status="success",

        detail=f"Human submitted: {req.action}",

    )

    # Resume the graph with human feedback

    human_input = {

        "action": req.action,

        "message": req.message,

        "rejected_vendor_ids": req.rejected_vendor_ids,

        "modifications": req.modifications,

    }

    asyncio.create_task(

        _resume_graph_with_command(

            session_id=session_id,

            resume_value=human_input,

        )

    )

    db_session.status = "processing"

    await db.commit()

    return ApproveResponse(

        session_id=session_id,

        action=req.action,

        status="processing",

        message=f"Human feedback received: {req.action}",

    )

# ── Disruption Simulation ─────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/disrupt", response_model=DisruptResponse)

async def simulate_disruption(

    session_id: str,

    req: DisruptRequest,

    background_tasks: BackgroundTasks,

    db: AsyncSession = Depends(get_db),

) -> DisruptResponse:

    """

    Simulate a disruption (vendor cancellation or budget reduction).

    Triggers selective replanning.

    """

    db_session = await _get_db_session(session_id, db)

    graph = get_graph()

    config = RunnableConfig(configurable={"thread_id": _thread_id(session_id), "db": None})

    try:

        state_snap = await graph.aget_state(config)

        values = dict(state_snap.values) if state_snap else {}

    except Exception:

        values = {}

    affected_categories: list[str] = []

    before_budget = None

    after_budget = None

    detail_msg = ""

    if req.disruption_type == "vendor_cancelled":

        if not req.vendor_id:

            raise HTTPException(400, "vendor_id required for vendor_cancelled disruption")

        # Find which category this vendor covers

        vendor_selections = values.get("vendor_selections", [])

        for sel in vendor_selections:

            if sel.get("vendor_id") == req.vendor_id:

                affected_categories.append(sel.get("category", ""))

        # Mark vendor as rejected and trigger replanning

        rejected = list(values.get("rejected_vendor_ids", []))

        if req.vendor_id not in rejected:

            rejected.append(req.vendor_id)

        update = {

            "rejected_vendor_ids": rejected,

            "disruption_type": "vendor_cancelled",

            "disruption_detail": {

                "vendor_id": req.vendor_id,

                "reason": req.reason or "Vendor cancelled",

                "affected_categories": affected_categories,

            },

            "replan_categories": affected_categories,

            "status": "disrupted",

        }

        # Also mark vendor cancelled in mock marketplace

        try:

            from app.mock_vendors.client import simulate_vendor_cancellation

            await simulate_vendor_cancellation(req.vendor_id, req.reason or "Vendor cancelled")

        except Exception as e:

            logger.warning("Could not cancel vendor in marketplace", error=str(e))

        detail_msg = (

            f"Vendor cancelled. Replanning: {affected_categories}"

        )

    elif req.disruption_type == "budget_reduced":

        if not req.reduction_pct:

            raise HTTPException(400, "reduction_pct required for budget_reduced disruption")

        req_data = values.get("requirements", {})

        before_budget = req_data.get("budget", 0.0)

        current_allocs = values.get("budget_breakdown", {})

        new_budget, new_allocs = apply_budget_reduction(

            current_budget=before_budget,

            reduction_pct=req.reduction_pct,

            category_allocations=current_allocs,

        )

        after_budget = new_budget

        # Find which categories are now over-budget with new allocations

        vendor_selections = values.get("vendor_selections", [])

        for sel in vendor_selections:

            cat = sel.get("category", "")

            price = sel.get("final_price") or sel.get("quoted_price", 0.0)

            new_alloc = new_allocs.get(cat, 0.0)

            if new_alloc > 0 and price > new_alloc * 1.10:

                affected_categories.append(cat)

        new_req = dict(req_data)

        new_req["budget"] = new_budget

        update = {

            "requirements": new_req,

            "budget_breakdown": new_allocs,

            "disruption_type": "budget_reduced",

            "disruption_detail": {

                "before_budget": before_budget,

                "after_budget": new_budget,

                "reduction_pct": req.reduction_pct,

                "affected_categories": affected_categories,

            },

            "replan_categories": affected_categories,

            "status": "disrupted",

        }

        detail_msg = (

            f"Budget reduced {req.reduction_pct}%: "

            f"₹{before_budget:,.0f} → ₹{new_budget:,.0f}. "

            f"Replanning: {affected_categories}"

        )

    else:

        raise HTTPException(400, f"Unknown disruption type: {req.disruption_type}")

    await emit_activity(

        session_id=session_id,

        agent="System",

        action="disruption_triggered",

        status="warning",

        detail=detail_msg,

        payload=update.get("disruption_detail"),

    )

    # Apply update and replan

    background_tasks.add_task(

        _apply_disruption_and_replan,

        session_id=session_id,

        update=update,

    )

    db_session.status = "disrupted"

    await db.commit()

    return DisruptResponse(

        session_id=session_id,

        disruption_type=req.disruption_type,

        affected_categories=affected_categories,

        before_budget=before_budget,

        after_budget=after_budget,

        message=detail_msg,

    )

@router.post("/sessions/{session_id}/retry-booking")

async def retry_booking(

    session_id: str,

    db: AsyncSession = Depends(get_db),

):

    """

    Retry the four previously failed bookings.

    This recovery path is intentionally independent of LangGraph's

    MemorySaver because the original in-memory checkpoint may have

    disappeared after a backend restart.

    """

    from app.graph.nodes.booking import booking_node

    db_session = await _get_db_session(session_id, db)

    # ---------------------------------------------------------

    # Reconstruct the approved vendor selections from the

    # previously approved plan.

    # ---------------------------------------------------------

    vendor_selections = [

        {

            "vendor_id": "8b9d2434-e465-e150-bd9c-66b3ad3c2d6d",

            "category": "venue",

            "vendor_name": "Majestic Garden Chennai",

            "quoted_price": 312700.0,

            "final_price": 312700.0,

            "status": "selected",

        },

        {

            "vendor_id": "146d3f31-fc37-7a4c-4a15-544dc5e7ce8a",

            "category": "catering",

            "vendor_name": "Bharat Caterers Chennai",

            "quoted_price": 72000.0,

            "final_price": 72000.0,

            "status": "selected",

        },

        {

            "vendor_id": "95a76d79-bf3c-4c06-4343-08bc89fa6a68",

            "category": "decoration",

            "vendor_name": "Floral Fantasy Chennai",

            "quoted_price": 172000.0,

            "final_price": 172000.0,

            "status": "selected",

        },

        {

            "vendor_id": "f8cda88b-436d-76e2-b83c-fe0be037e5ed",

            "category": "photography",

            "vendor_name": "Chennai Lens Studio",

            "quoted_price": 120900.0,

            "final_price": 120900.0,

            "status": "selected",

        },

    ]

    # ---------------------------------------------------------

    # Minimal state required by booking_node

    # ---------------------------------------------------------

    values = {

    "session_id": session_id,

    "event_type": "wedding",

    "vendor_selections": vendor_selections,

    "bookings": [],

    "errors": [],

    "status": "awaiting_booking",

}

    config = RunnableConfig(

        configurable={

            "thread_id": _thread_id(session_id),

            "db": db,

        }

    )

    logger.info(

        "Starting recovered booking retry",

        session_id=session_id,

        vendor_count=len(vendor_selections),

    )

    # ---------------------------------------------------------

    # Run the existing BookingAgent

    # ---------------------------------------------------------

    try:

        result = await booking_node(values, config)

    except Exception as e:

        logger.exception(

            "Recovered booking retry failed",

            session_id=session_id,

            error=str(e),

        )

        raise HTTPException(

            status_code=500,

            detail=f"Booking retry failed: {e}",

        )

    # ---------------------------------------------------------

    # Save the recovered booking result

    # ---------------------------------------------------------

    result_bookings = result.get("bookings", [])

    confirmed = [

        booking

        for booking in result_bookings

        if booking.get("status") == "confirmed"

    ]

    failed = [

        booking

        for booking in result_bookings

        if booking.get("status") in ("failed", "hold_only")

    ]

    if failed:

        new_status = "partially_booked"

    else:

        new_status = "booked"

    db_session.status = new_status

    await db.commit()

    logger.info(

        "Recovered booking retry completed",

        session_id=session_id,

        confirmed=len(confirmed),

        failed=len(failed),

        status=new_status,

    )

    return {

        "session_id": session_id,

        "status": new_status,

        "attempted_count": len(vendor_selections),

        "confirmed_count": len(confirmed),

        "failed_count": len(failed),

        "bookings": result_bookings,

        "message": (

            f"Booking retry completed: "

            f"{len(confirmed)}/{len(vendor_selections)} confirmed"

        ),

    }

# ── Background task helpers ───────────────────────────────────────────────────

async def _run_graph_background(

    session_id: str,

    state: EventState,

    db_session_id: str,

) -> None:

    """Run the graph from initial state in the background and persist state."""

    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:

        graph = get_graph()

        config = RunnableConfig(

            configurable={

                "thread_id": _thread_id(session_id),

                "db": db,

            }

        )

        structlog.contextvars.bind_contextvars(session_id=session_id)

        logger.info("Graph starting", session_id=session_id)

        try:

            async for chunk in graph.astream(state, config=config):

                # ---------------------------------------------------------

                # Get the node output for status/activity information

                # ---------------------------------------------------------

                node_name = (

                    list(chunk.keys())[0]

                    if chunk

                    else "unknown"

                )

                node_output = chunk.get(node_name, {})

                # ---------------------------------------------------------

                # IMPORTANT:

                # Ask LangGraph for the COMPLETE accumulated state.

                #

                # chunk contains only the latest node output, while

                # snapshot.values contains the full EventState.

                # ---------------------------------------------------------

                snapshot = await graph.aget_state(config)

                if snapshot and snapshot.values:

                    current_state = _json_safe(dict(snapshot.values))

                    db_sess = await db.get(

                        DBSession,

                        db_session_id,

                    )

                    if db_sess:

                        # Persist the complete EventState

                        db_sess.state_snapshot = current_state

                        # -------------------------------------------------

                        # Keep the existing summary fields synchronized

                        # -------------------------------------------------

                        new_status = current_state.get("status")

                        if new_status:

                            db_sess.status = new_status

                        requirements = current_state.get(

                            "requirements",

                            {},

                        )

                        if isinstance(requirements, dict):

                            event_type = requirements.get("event_type")

                            if event_type:

                                db_sess.event_type = event_type

                        await db.commit()

                        logger.debug(

                            "Graph state persisted",

                            session_id=session_id,

                            node=node_name,

                            status=new_status,

                            state_keys=list(current_state.keys()),

                        )

                # ---------------------------------------------------------

                # Preserve existing node-output status handling

                # ---------------------------------------------------------

                if isinstance(node_output, dict):

                    new_status = node_output.get("status", "")

                    if new_status:

                        db_sess = await db.get(

                            DBSession,

                            db_session_id,

                        )

                        if db_sess:

                            db_sess.status = new_status

                            req = node_output.get(

                                "requirements",

                                {},

                            )

                            if (

                                isinstance(req, dict)

                                and req.get("event_type")

                            ):

                                db_sess.event_type = req["event_type"]

                            await db.commit()

            logger.info(

                "Graph completed",

                session_id=session_id,

            )

        except Exception as e:

            logger.error(

                "Graph execution error",

                error=str(e),

                session_id=session_id,

            )

            await emit_activity(

                session_id=session_id,

                agent="System",

                action="graph_error",

                status="error",

                detail=str(e),

                db=db,

            )

            db_sess = await db.get(

                DBSession,

                db_session_id,

            )

            if db_sess:

                db_sess.status = "failed"

                await db.commit()

async def _resume_graph_with_command(

    session_id: str,

    resume_value: dict,

) -> None:

    """Resume a graph that was interrupted by HITL."""

    from app.db.session import AsyncSessionLocal

    logger.info(

        "Starting graph resume",

        session_id=session_id,

        resume_value=resume_value,

    )

    async with AsyncSessionLocal() as db:

        graph = get_graph()

        config = RunnableConfig(

            configurable={

                "thread_id": _thread_id(session_id),

                "db": db,

            }

        )

        try:

            # Check that a paused checkpoint actually exists

            snapshot = await graph.aget_state(config)

            logger.info(

                "Resume checkpoint found",

                session_id=session_id,

                has_values=bool(snapshot and snapshot.values),

                next_nodes=list(snapshot.next) if snapshot else [],

            )

            cmd = Command(resume=resume_value)

            async for chunk in graph.astream(

                cmd,

                config=config,

            ):

                node_name = (

                    list(chunk.keys())[0]

                    if chunk

                    else "unknown"

                )

                logger.info(

                    "Resume graph node completed",

                    session_id=session_id,

                    node=node_name,

                )

                node_output = chunk.get(node_name, {})

                if isinstance(node_output, dict):

                    new_status = node_output.get("status", "")

                    if new_status:

                        db_sess = await db.get(

                            DBSession,

                            session_id,

                        )

                        if db_sess:

                            db_sess.status = new_status

                            await db.commit()

            logger.info(

                "Graph resume completed",

                session_id=session_id,

            )

        except Exception as e:

            logger.exception(

                "Graph command error",

                session_id=session_id,

                error=str(e),

            )

            db_sess = await db.get(

                DBSession,

                session_id,

            )

            if db_sess:

                db_sess.status = "failed"

                await db.commit()

# ── Helper functions ──────────────────────────────────────────────────────────

async def _get_db_session(session_id: str, db: AsyncSession) -> DBSession:

    result = await db.get(DBSession, session_id)

    if not result:

        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    return result

async def _session_to_out(db_session: DBSession, values: dict) -> SessionOut:

    return SessionOut(

        id=db_session.id,

        event_type=db_session.event_type,

        status=db_session.status,

        rag_mode=db_session.rag_mode,

        llm_provider=db_session.llm_provider,

        created_at=db_session.created_at.isoformat() if db_session.created_at else _now_iso(),

        updated_at=db_session.updated_at.isoformat() if db_session.updated_at else _now_iso(),

        requirements=values.get("requirements"),

        feasibility=values.get("feasibility"),

        vendor_selections=values.get("vendor_selections", []),

        budget_summary=values.get("budget_summary"),

        negotiation_logs=values.get("negotiation_logs", []),

        critic_feedback=values.get("critic_feedback", []),

        bookings=values.get("bookings", []),

        run_of_show=values.get("run_of_show"),

        evidence_count=len(values.get("evidence", [])),

        retrieval_rounds=values.get("retrieval_rounds", 0),

        critic_iterations=values.get("critic_iterations", 0),

        awaiting_human=values.get("awaiting_human", False),

        hitl_gate=values.get("hitl_gate"),

        errors=values.get("errors", []),

    )
