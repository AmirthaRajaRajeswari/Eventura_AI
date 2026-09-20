"""
Mock Vendor Marketplace router.

Exposes a realistic vendor API that the main application communicates
with via HTTP client calls. Never import this router's logic directly
into the agent code — always go through the HTTP client.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Vendor, VendorAvailability, Booking
from app.db.session import get_db
from app.mock_vendors.schemas import (
    AvailabilityOut,
    CancelSimulationOut,
    CancelSimulationRequest,
    ConfirmOut,
    ConfirmRequest,
    HoldOut,
    HoldRequest,
    NegotiateOut,
    NegotiateRequest,
    QuoteOut,
    QuoteRequest,
    VendorListOut,
    VendorOut,
)

router = APIRouter(prefix="/mock-vendors", tags=["mock-vendors"])

SYNTHETIC_DISCLAIMER = (
    "Demo vendor and pricing data are synthetic and used for demonstration purposes only."
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ref() -> str:
    return str(uuid.uuid4())[:12].upper()


# ── Vendor listing ────────────────────────────────────────────────────────────

@router.get("/vendors", response_model=VendorListOut)
async def list_vendors(
    city: str | None = Query(None),
    category: str | None = Query(None),
    event_type: str | None = Query(None),
    min_capacity: int | None = Query(None),
    max_price: float | None = Query(None),
    date: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> VendorListOut:
    """Return vendors matching the given filters."""
    q = select(Vendor).where(Vendor.is_active == True)

    if city:
        q = q.where(Vendor.city.ilike(f"%{city}%"))
    if category:
        q = q.where(Vendor.category == category)
    if event_type:
        q = q.where(Vendor.event_types.any(event_type))
    if min_capacity:
        q = q.where(
            (Vendor.max_capacity.is_(None)) | (Vendor.max_capacity >= min_capacity)
        )
    if max_price:
        q = q.where(
            (Vendor.base_price <= max_price) | (Vendor.base_price == 0)
        )

    # Filter by availability if date provided
    if date:
        unavailable_subq = (
            select(VendorAvailability.vendor_id)
            .where(
                and_(
                    VendorAvailability.date == date,
                    VendorAvailability.is_available == False,
                )
            )
        )
        q = q.where(Vendor.id.not_in(unavailable_subq))

    total_q = q
    result = await db.execute(q.offset(offset).limit(limit))
    vendors = result.scalars().all()

    return VendorListOut(
        vendors=[_to_vendor_out(v) for v in vendors],
        total=len(vendors),
    )


@router.get("/vendors/{vendor_id}", response_model=VendorOut)
async def get_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
) -> VendorOut:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id!r} not found")
    return _to_vendor_out(vendor)


# ── Availability ──────────────────────────────────────────────────────────────

@router.get("/vendors/{vendor_id}/availability", response_model=list[AvailabilityOut])
async def check_availability(
    vendor_id: str,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> list[AvailabilityOut]:
    result = await db.execute(
        select(VendorAvailability).where(
            and_(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.date >= start_date,
                VendorAvailability.date <= end_date,
            )
        )
    )
    records = result.scalars().all()

    return [
        AvailabilityOut(
            vendor_id=r.vendor_id,
            date=r.date,
            is_available=r.is_available,
        )
        for r in records
    ]


# ── Quote ─────────────────────────────────────────────────────────────────────

@router.post("/vendors/{vendor_id}/quote", response_model=QuoteOut)
async def get_quote(
    vendor_id: str,
    request: QuoteRequest,
    db: AsyncSession = Depends(get_db),
) -> QuoteOut:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id!r} not found")

    quoted, breakdown = _calculate_price(vendor, request.guest_count, request.duration_days)
    valid_until = (_now_utc() + timedelta(hours=48)).isoformat()

    return QuoteOut(
        vendor_id=vendor_id,
        vendor_name=vendor.name,
        category=vendor.category,
        date=request.date,
        guest_count=request.guest_count,
        quoted_price=quoted,
        price_breakdown=breakdown,
        valid_until=valid_until,
    )


# ── Hold ──────────────────────────────────────────────────────────────────────

@router.post("/vendors/{vendor_id}/hold", response_model=HoldOut)
async def place_hold(
    vendor_id: str,
    request: HoldRequest,
    db: AsyncSession = Depends(get_db),
) -> HoldOut:
    result = await db.execute(
        select(VendorAvailability).where(
            and_(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.date == request.date,
            )
        )
    )
    avail = result.scalar_one_or_none()

    if avail and not avail.is_available:
        raise HTTPException(
            status_code=409,
            detail=f"Vendor {vendor_id!r} is not available on {request.date}",
        )

    if avail:
        avail.is_available = False
        avail.booked_by_session = request.session_id
    else:
        avail = VendorAvailability(
            id=str(uuid.uuid4()),
            vendor_id=vendor_id,
            date=request.date,
            is_available=False,
            booked_by_session=request.session_id,
        )
        db.add(avail)

    await db.commit()

    hold_ref = f"HOLD-{_ref()}"
    expires_at = (_now_utc() + timedelta(hours=24)).isoformat()

    return HoldOut(
        hold_reference=hold_ref,
        vendor_id=vendor_id,
        session_id=request.session_id,
        date=request.date,
        status="held",
        expires_at=expires_at,
    )


# ── Confirm ───────────────────────────────────────────────────────────────────

@router.post("/vendors/{vendor_id}/confirm", response_model=ConfirmOut)
async def confirm_booking(
    vendor_id: str,
    request: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> ConfirmOut:
    """
    Confirm a vendor booking. This is an IRREVERSIBLE action.
    Must only be called after explicit human approval.
    """
    # Verify vendor exists
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id!r} not found")

    confirm_ref = f"CNF-{_ref()}"

    return ConfirmOut(
        confirmation_reference=confirm_ref,
        vendor_id=vendor_id,
        session_id=request.session_id,
        status="confirmed",
        final_price=request.final_price,
        confirmed_at=_now_utc().isoformat(),
    )


# ── Negotiate ─────────────────────────────────────────────────────────────────

@router.post("/vendors/{vendor_id}/negotiate", response_model=NegotiateOut)
async def negotiate(
    vendor_id: str,
    request: NegotiateRequest,
    db: AsyncSession = Depends(get_db),
) -> NegotiateOut:
    """
    Rule-based vendor negotiation.

    Each vendor has a hidden price floor. The vendor-side response is
    deterministic (rule-based), not LLM-driven.
    """
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id!r} not found")

    # Apply rule-based negotiation logic
    response = _negotiate_rules(vendor, request.offer_price, request.round_number)
    return response


# ── Admin: simulate cancellation ──────────────────────────────────────────────

@router.post("/admin/simulate/cancel/{vendor_id}", response_model=CancelSimulationOut)
async def simulate_cancellation(
    vendor_id: str,
    request: CancelSimulationRequest,
    db: AsyncSession = Depends(get_db),
) -> CancelSimulationOut:
    """
    Demo disruption: mark a vendor as cancelled/inactive.
    Returns list of sessions that had holds/bookings with this vendor.
    """
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id!r} not found")

    # Find affected sessions
    bookings_result = await db.execute(
        select(Booking).where(
            and_(
                Booking.vendor_id == vendor_id,
                Booking.status.in_(["pending", "hold", "confirmed"]),
            )
        )
    )
    affected_bookings = bookings_result.scalars().all()
    affected_sessions = list({b.session_id for b in affected_bookings})

    # Mark vendor inactive
    vendor.is_active = False
    await db.commit()

    return CancelSimulationOut(
        vendor_id=vendor_id,
        status="cancelled",
        reason=request.reason,
        affected_sessions=affected_sessions,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_vendor_out(vendor: Vendor) -> VendorOut:
    return VendorOut(
        id=vendor.id,
        name=vendor.name,
        category=vendor.category,
        event_types=vendor.event_types,
        city=vendor.city,
        state=vendor.state,
        base_price=vendor.base_price,
        price_per_guest=vendor.price_per_guest,
        min_capacity=vendor.min_capacity,
        max_capacity=vendor.max_capacity,
        rating=vendor.rating,
        tags=vendor.tags,
        description=vendor.description,
        contact_phone=vendor.contact_phone,
        min_notice_days=vendor.min_notice_days,
        is_active=vendor.is_active,
        is_synthetic=vendor.is_synthetic,
    )


def _calculate_price(
    vendor: Vendor,
    guest_count: int | None,
    duration_days: int,
) -> tuple[float, dict[str, float]]:
    """
    Deterministic price calculation — no LLM involvement.

    Returns (total_price, breakdown_dict).
    """
    breakdown: dict[str, float] = {}

    if vendor.price_per_guest and guest_count:
        catering_cost = round(vendor.price_per_guest * guest_count, 2)
        breakdown["per_guest_cost"] = catering_cost
        base = catering_cost
    else:
        base = vendor.base_price
        breakdown["base_price"] = base

    # Multi-day events: day 2+ at 70% of base rate
    if duration_days > 1:
        extra_days_cost = round(base * 0.70 * (duration_days - 1), 2)
        breakdown["extra_days_cost"] = extra_days_cost
        total = base + extra_days_cost
    else:
        total = base

    total = round(total, 2)
    breakdown["total"] = total
    return total, breakdown


def _negotiate_rules(
    vendor: Vendor,
    offer_price: float,
    round_number: int,
) -> NegotiateOut:
    """
    Rule-based vendor negotiation response.

    Rules:
    - If offer >= quoted price: accept
    - If offer >= price_floor AND round == 1: counter at midpoint
    - If offer >= price_floor AND round >= 2: accept (vendor concedes)
    - If offer < price_floor: reject
    """
    # Quoted price is base_price (or a default for per-guest vendors)
    quoted_price = vendor.base_price if vendor.base_price > 0 else 50_000.0
    price_floor = vendor.price_floor

    if offer_price >= quoted_price:
        return NegotiateOut(
            vendor_id=vendor.id,
            round_number=round_number,
            our_offer=offer_price,
            vendor_response="accepted",
            counter_price=None,
            final_price=offer_price,
            message=(
                f"We're pleased to accept your offer of ₹{offer_price:,.0f}. "
                f"We look forward to serving you!"
            ),
        )
    elif offer_price >= price_floor and round_number == 1:
        # Counter at midpoint between offer and quoted
        counter = round((offer_price + quoted_price) / 2, -2)
        return NegotiateOut(
            vendor_id=vendor.id,
            round_number=round_number,
            our_offer=offer_price,
            vendor_response="counter",
            counter_price=counter,
            final_price=None,
            message=(
                f"Thank you for your offer of ₹{offer_price:,.0f}. "
                f"Our best counter-offer is ₹{counter:,.0f}. "
                f"This is inclusive of all services as quoted."
            ),
        )
    elif offer_price >= price_floor and round_number >= 2:
        # Vendor accepts on second round to close the deal
        return NegotiateOut(
            vendor_id=vendor.id,
            round_number=round_number,
            our_offer=offer_price,
            vendor_response="accepted",
            counter_price=None,
            final_price=offer_price,
            message=(
                f"We appreciate your commitment. "
                f"We'll honour your offer of ₹{offer_price:,.0f}. "
                f"Please confirm the booking at your earliest convenience."
            ),
        )
    else:
        # Below floor — reject
        return NegotiateOut(
            vendor_id=vendor.id,
            round_number=round_number,
            our_offer=offer_price,
            vendor_response="rejected",
            counter_price=None,
            final_price=None,
            message=(
                f"We regret we cannot accept an offer below ₹{price_floor:,.0f}. "
                f"Our costs do not allow further reduction."
            ),
        )
