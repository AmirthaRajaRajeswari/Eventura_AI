"""
Booking Agent — Eventura AI

ONLY executes after explicit human approval (HITL Gate #1).
NEVER called without approval — this is an irreversible action.

Flow:
  place_hold → confirm_booking → update state

All booking calls go through the mock vendor HTTP client.
"""

from __future__ import annotations

from app.graph.activity import emit_activity
from app.graph.state import BookingRecord, EventState
from app.logger import get_logger
from app.mock_vendors.client import confirm_booking, place_hold

logger = get_logger(__name__)


async def booking_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Booking Agent.
    Executes only after human approval. Irreversible.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")
    req = state.get("requirements", {})
    vendor_selections = state.get("vendor_selections", [])
    date_str = req.get("date", "")
    duration_days = req.get("duration_days", 1)
    guest_count = req.get("guest_count")

    await emit_activity(
        session_id=session_id,
        agent="BookingAgent",
        action="start_booking",
        status="running",
        detail=f"Booking {len(vendor_selections)} vendors (post-approval)…",
        db=db,
    )

    bookings: list[BookingRecord] = list(state.get("bookings", []))
    updated_selections = list(vendor_selections)
    errors = list(state.get("errors", []))

    for idx, sel in enumerate(vendor_selections):
        vendor_id = sel.get("vendor_id", "")
        category = sel.get("category", "")
        final_price = sel.get("final_price") or sel.get("quoted_price", 0.0)

        await emit_activity(
            session_id=session_id,
            agent="BookingAgent",
            action="place_hold",
            status="running",
            detail=f"Placing hold: {sel.get('name')} ({category})…",
            db=db,
        )

        # ── Step 1: Place hold ────────────────────────────────────────────
        try:
            hold_result = await place_hold(
                vendor_id=vendor_id,
                session_id=session_id,
                date=date_str,
                guest_count=guest_count if category in ("venue", "catering") else None,
                duration_days=duration_days,
            )
            hold_ref = hold_result.get("hold_reference", "")

            await emit_activity(
                session_id=session_id,
                agent="BookingAgent",
                action="place_hold",
                status="success",
                detail=f"Hold placed: {hold_ref} for {sel.get('name')}",
                db=db,
            )
        except Exception as e:
            error_msg = f"Hold failed for {sel.get('name')}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            await emit_activity(
                session_id=session_id,
                agent="BookingAgent",
                action="place_hold",
                status="error",
                detail=error_msg,
                db=db,
            )
            bookings.append(BookingRecord(
                vendor_id=vendor_id,
                category=category,
                status="failed",
                quoted_price=sel.get("quoted_price", 0.0),
                final_price=final_price,
                hold_reference=None,
                confirmation_reference=None,
            ))
            continue

        # ── Step 2: Confirm booking (IRREVERSIBLE) ────────────────────────
        await emit_activity(
            session_id=session_id,
            agent="BookingAgent",
            action="confirm_booking",
            status="running",
            detail=f"Confirming booking: {sel.get('name')} @ ₹{final_price:,.0f}…",
            db=db,
        )

        try:
            confirm_result = await confirm_booking(
                vendor_id=vendor_id,
                session_id=session_id,
                hold_reference=hold_ref,
                final_price=final_price,
            )
            confirm_ref = confirm_result.get("confirmation_reference", "")

            booking = BookingRecord(
                vendor_id=vendor_id,
                category=category,
                status="confirmed",
                quoted_price=sel.get("quoted_price", 0.0),
                final_price=final_price,
                hold_reference=hold_ref,
                confirmation_reference=confirm_ref,
            )
            bookings.append(booking)

            updated_selections[idx] = {**sel, "status": "booked"}

            await emit_activity(
                session_id=session_id,
                agent="BookingAgent",
                action="confirm_booking",
                status="success",
                detail=f"Confirmed: {sel.get('name')} [{confirm_ref}] @ ₹{final_price:,.0f}",
                db=db,
            )

            # Persist to DB
            if db is not None:
                from app.db.models import Booking
                db_booking = Booking(
                    session_id=session_id,
                    vendor_id=vendor_id,
                    category=category,
                    status="confirmed",
                    quoted_price=sel.get("quoted_price", 0.0),
                    final_price=final_price,
                    hold_reference=hold_ref,
                    confirmation_reference=confirm_ref,
                )
                db.add(db_booking)
                await db.flush()

        except Exception as e:
            error_msg = f"Confirmation failed for {sel.get('name')}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            bookings.append(BookingRecord(
                vendor_id=vendor_id,
                category=category,
                status="hold_only",
                quoted_price=sel.get("quoted_price", 0.0),
                final_price=final_price,
                hold_reference=hold_ref,
                confirmation_reference=None,
            ))
            await emit_activity(
                session_id=session_id,
                agent="BookingAgent",
                action="confirm_booking",
                status="error",
                detail=error_msg,
                db=db,
            )

    confirmed = [b for b in bookings if b.get("status") == "confirmed"]
    await emit_activity(
        session_id=session_id,
        agent="BookingAgent",
        action="booking_complete",
        status="success" if not errors else "warning",
        detail=f"{len(confirmed)}/{len(vendor_selections)} bookings confirmed",
        db=db,
    )

    return {
        "bookings": bookings,
        "vendor_selections": updated_selections,
        "errors": errors,
        "status": "completed" if not errors else "partially_booked",
    }


