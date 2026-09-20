"""
Pydantic schemas for the Mock Vendor Marketplace API.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VendorOut(BaseModel):
    id: str
    name: str
    category: str
    event_types: list[str]
    city: str
    state: str | None
    base_price: float
    price_per_guest: float | None
    min_capacity: int | None
    max_capacity: int | None
    rating: float
    tags: list[str]
    description: str | None
    contact_phone: str | None
    min_notice_days: int
    is_active: bool
    is_synthetic: bool = True
    synthetic_disclaimer: str = (
        "Demo vendor and pricing data are synthetic and used for demonstration purposes only."
    )


class VendorListOut(BaseModel):
    vendors: list[VendorOut]
    total: int
    synthetic_disclaimer: str = (
        "Demo vendor and pricing data are synthetic and used for demonstration purposes only."
    )


class AvailabilityOut(BaseModel):
    vendor_id: str
    date: str
    is_available: bool


class QuoteRequest(BaseModel):
    date: str
    guest_count: int | None = None
    duration_days: int = 1


class QuoteOut(BaseModel):
    vendor_id: str
    vendor_name: str
    category: str
    date: str
    guest_count: int | None
    quoted_price: float
    price_breakdown: dict[str, float]
    valid_until: str
    synthetic_disclaimer: str = (
        "Demo vendor and pricing data are synthetic and used for demonstration purposes only."
    )


class HoldRequest(BaseModel):
    session_id: str
    date: str
    guest_count: int | None = None
    duration_days: int = 1


class HoldOut(BaseModel):
    hold_reference: str
    vendor_id: str
    session_id: str
    date: str
    status: str  # "held"
    expires_at: str


class ConfirmRequest(BaseModel):
    session_id: str
    hold_reference: str
    final_price: float


class ConfirmOut(BaseModel):
    confirmation_reference: str
    vendor_id: str
    session_id: str
    status: str  # "confirmed"
    final_price: float
    confirmed_at: str


class NegotiateRequest(BaseModel):
    session_id: str
    offer_price: float
    round_number: int = 1  # 1 or 2
    context: str | None = None


class NegotiateOut(BaseModel):
    vendor_id: str
    round_number: int
    our_offer: float
    vendor_response: str  # "accepted" | "counter" | "rejected"
    counter_price: float | None
    final_price: float | None
    message: str


class CancelSimulationRequest(BaseModel):
    reason: str = "Vendor cancelled due to double booking"


class CancelSimulationOut(BaseModel):
    vendor_id: str
    status: str  # "cancelled"
    reason: str
    affected_sessions: list[str]
