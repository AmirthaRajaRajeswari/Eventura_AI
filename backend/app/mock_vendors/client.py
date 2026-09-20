"""
HTTP client for the Mock Vendor Marketplace.

All agent code must use these functions to interact with vendors.
Never import router logic directly — maintain the HTTP boundary.
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


def _base_url() -> str:
    return settings.mock_vendor_base_url.rstrip("/")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{_base_url()}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{_base_url()}{path}", json=body)
        resp.raise_for_status()
        return resp.json()


# ── Public API ────────────────────────────────────────────────────────────────

async def search_vendors(
    city: str | None = None,
    category: str | None = None,
    event_type: str | None = None,
    min_capacity: int | None = None,
    max_price: float | None = None,
    date: str | None = None,
    limit: int = 20,
) -> dict:
    """Search vendors by filter criteria."""
    params: dict[str, Any] = {"limit": limit}
    if city:
        params["city"] = city
    if category:
        params["category"] = category
    if event_type:
        params["event_type"] = event_type
    if min_capacity:
        params["min_capacity"] = min_capacity
    if max_price:
        params["max_price"] = max_price
    if date:
        params["date"] = date

    logger.debug("Searching vendors", params=params)
    return await _get("/mock-vendors/vendors", params=params)


async def get_vendor(vendor_id: str) -> dict:
    """Fetch a single vendor by ID."""
    return await _get(f"/mock-vendors/vendors/{vendor_id}")


async def check_availability(
    vendor_id: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Check vendor availability for a date range."""
    return await _get(
        f"/mock-vendors/vendors/{vendor_id}/availability",
        params={"start_date": start_date, "end_date": end_date},
    )


async def get_quote(
    vendor_id: str,
    date: str,
    guest_count: int | None = None,
    duration_days: int = 1,
) -> dict:
    """Get a price quote from a vendor."""
    return await _post(
        f"/mock-vendors/vendors/{vendor_id}/quote",
        body={
            "date": date,
            "guest_count": guest_count,
            "duration_days": duration_days,
        },
    )


async def place_hold(
    vendor_id: str,
    session_id: str,
    date: str,
    guest_count: int | None = None,
    duration_days: int = 1,
) -> dict:
    """Place a reversible hold on a vendor slot."""
    return await _post(
        f"/mock-vendors/vendors/{vendor_id}/hold",
        body={
            "session_id": session_id,
            "date": date,
            "guest_count": guest_count,
            "duration_days": duration_days,
        },
    )


async def confirm_booking(
    vendor_id: str,
    session_id: str,
    hold_reference: str,
    final_price: float,
) -> dict:
    """
    Confirm a vendor booking.

    IRREVERSIBLE — only call after explicit human approval.
    """
    return await _post(
        f"/mock-vendors/vendors/{vendor_id}/confirm",
        body={
            "session_id": session_id,
            "hold_reference": hold_reference,
            "final_price": final_price,
        },
    )


async def negotiate(
    vendor_id: str,
    session_id: str,
    offer_price: float,
    round_number: int = 1,
    context: str | None = None,
) -> dict:
    """Send a negotiation offer to a vendor."""
    return await _post(
        f"/mock-vendors/vendors/{vendor_id}/negotiate",
        body={
            "session_id": session_id,
            "offer_price": offer_price,
            "round_number": round_number,
            "context": context,
        },
    )


async def simulate_vendor_cancellation(
    vendor_id: str,
    reason: str = "Vendor cancelled due to double booking",
) -> dict:
    """Admin: simulate a vendor cancellation for disruption demo."""
    return await _post(
        f"/mock-vendors/admin/simulate/cancel/{vendor_id}",
        body={"reason": reason},
    )
