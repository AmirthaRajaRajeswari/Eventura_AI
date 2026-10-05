"""
SQL-based vendor retrieval for Eventura AI.

All vendor lookups go through deterministic SQL queries.

The LLM is never asked to find or select vendors — it only explains results.

Retrieval modes:

  - Direct SQL with explicit filters (city, category, capacity, price, date)
  - Exclusion of previously rejected vendors
  - Returns structured VendorResult objects with evidence IDs attached
"""

from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Vendor, VendorAvailability
from app.logger import get_logger
from app.retrieval.evidence import Evidence, make_evidence

logger = get_logger(__name__)


@dataclass
class VendorResult:
    """A vendor returned by retrieval with full pricing and evidence."""

    vendor_id: str
    name: str
    category: str
    city: str
    base_price: float
    price_per_guest: float | None
    price_floor: float
    min_capacity: int | None
    max_capacity: int | None
    rating: float
    tags: list[str]
    description: str | None
    is_available: bool
    evidence: Evidence

    def estimated_price(
        self,
        guest_count: int | None,
        duration_days: int = 1,
    ) -> float:
        """
        Deterministic price estimate — no LLM arithmetic.
        """

        if self.price_per_guest and guest_count:
            base = self.price_per_guest * guest_count
        else:
            base = self.base_price

        if duration_days > 1:
            total = base + base * 0.70 * (duration_days - 1)
        else:
            total = base

        return round(total, 2)

    def to_dict(self) -> dict:
        return {
            "vendor_id": self.vendor_id,
            "name": self.name,
            "category": self.category,
            "city": self.city,
            "base_price": self.base_price,
            "price_per_guest": self.price_per_guest,
            "price_floor": self.price_floor,
            "min_capacity": self.min_capacity,
            "max_capacity": self.max_capacity,
            "rating": self.rating,
            "tags": self.tags,
            "description": self.description,
            "is_available": self.is_available,
            "evidence_ids": [self.evidence.evidence_id],
        }


async def retrieve_vendors(
    db: AsyncSession,
    session_id: str,
    category: str,
    event_type: str,
    city: str,
    date: str | None = None,
    min_capacity: int | None = None,
    max_price: float | None = None,
    retrieval_round: int = 0,
    limit: int = 10,
    rejected_vendor_ids: list[str] | None = None,
) -> list[VendorResult]:
    """
    Retrieve vendors matching structured filters via SQL.

    rejected_vendor_ids:
        Vendor IDs that were rejected by the Critic/Planner.
        These vendors are excluded directly at the SQL layer so
        Agentic RAG cannot retrieve them again.
    """

    rejected_vendor_ids = rejected_vendor_ids or []

    logger.debug(
        "SQL vendor retrieval",
        category=category,
        city=city,
        event_type=event_type,
        date=date,
        min_capacity=min_capacity,
        max_price=max_price,
        retrieval_round=retrieval_round,
        rejected_vendor_count=len(rejected_vendor_ids),
    )

    # ------------------------------------------------------------------
    # Build base query
    # ------------------------------------------------------------------
    q = (
        select(Vendor)
        .where(Vendor.is_active == True)
        .where(Vendor.category == category)
        .where(Vendor.city.ilike(f"%{city}%"))
        .where(Vendor.event_types.any(event_type))
    )

    # ------------------------------------------------------------------
    # CRITICAL:
    # Never retrieve vendors explicitly rejected during replanning.
    # ------------------------------------------------------------------
    if rejected_vendor_ids:
        q = q.where(
            Vendor.id.not_in(rejected_vendor_ids)
        )

    # ------------------------------------------------------------------
    # Capacity filter
    # ------------------------------------------------------------------
    if min_capacity is not None:
        q = q.where(
            (Vendor.max_capacity.is_(None))
            | (Vendor.max_capacity >= min_capacity)
        )

    # ------------------------------------------------------------------
    # Price filter
    # ------------------------------------------------------------------
    if max_price is not None:
        q = q.where(
            (Vendor.base_price <= max_price)
            | (Vendor.price_per_guest.isnot(None))
        )

    # ------------------------------------------------------------------
    # Exclude vendors unavailable on requested date
    # ------------------------------------------------------------------
    if date:
        unavailable_subq = (
            select(VendorAvailability.vendor_id)
            .where(
                and_(
                    VendorAvailability.date == date,
                    VendorAvailability.is_available == False,
                )
            )
            .scalar_subquery()
        )

        q = q.where(
            Vendor.id.not_in(unavailable_subq)
        )

    # ------------------------------------------------------------------
    # Highest-rated vendors first
    # ------------------------------------------------------------------
    q = (
        q.order_by(Vendor.rating.desc())
        .limit(limit)
    )

    result = await db.execute(q)
    vendors = result.scalars().all()

    logger.debug(
        "SQL vendor retrieval results",
        count=len(vendors),
    )

    results: list[VendorResult] = []

    for vendor in vendors:

        # --------------------------------------------------------------
        # Check specific-date availability
        # --------------------------------------------------------------
        is_available = True

        if date:
            avail_result = await db.execute(
                select(VendorAvailability).where(
                    and_(
                        VendorAvailability.vendor_id == vendor.id,
                        VendorAvailability.date == date,
                    )
                )
            )

            avail = avail_result.scalar_one_or_none()

            is_available = (
                avail.is_available
                if avail
                else True
            )

        # --------------------------------------------------------------
        # Evidence summary
        # --------------------------------------------------------------
        content_summary = (
            f"Vendor: {vendor.name} | "
            f"Category: {vendor.category} | "
            f"City: {vendor.city} | "
            f"Rating: {vendor.rating} | "
            f"Base price: INR{vendor.base_price:,.0f} | "
            f"Price floor: INR{vendor.price_floor:,.0f} | "
            f"Capacity: {vendor.min_capacity}-{vendor.max_capacity} | "
            f"Tags: {', '.join(vendor.tags or [])}"
        )

        query_str = (
            f"category={category} "
            f"city={city} "
            f"event_type={event_type}"
            + (
                f" date={date}"
                if date
                else ""
            )
            + (
                f" min_capacity={min_capacity}"
                if min_capacity
                else ""
            )
            + (
                f" max_price={max_price}"
                if max_price
                else ""
            )
            + (
                f" excluded_vendor_ids={rejected_vendor_ids}"
                if rejected_vendor_ids
                else ""
            )
        )

        evidence = make_evidence(
            session_id=session_id,
            source_type="vendor_sql",
            source_ref=vendor.id,
            content=content_summary,
            score=vendor.rating / 5.0,
            query=query_str,
            retrieval_round=retrieval_round,
            metadata={
                "vendor_id": vendor.id,
                "category": vendor.category,
                "city": vendor.city,
            },
        )

        results.append(
            VendorResult(
                vendor_id=vendor.id,
                name=vendor.name,
                category=vendor.category,
                city=vendor.city,
                base_price=vendor.base_price,
                price_per_guest=vendor.price_per_guest,
                price_floor=vendor.price_floor,
                min_capacity=vendor.min_capacity,
                max_capacity=vendor.max_capacity,
                rating=vendor.rating,
                tags=vendor.tags or [],
                description=vendor.description,
                is_available=is_available,
                evidence=evidence,
            )
        )

    return results


async def get_cheapest_vendor(
    db: AsyncSession,
    category: str,
    event_type: str,
    city: str,
    guest_count: int | None = None,
) -> VendorResult | None:
    """
    Find the cheapest vendor for a category.

    Used by the Feasibility Agent for deterministic minimum cost calculation.
    """

    q = (
        select(Vendor)
        .where(Vendor.is_active == True)
        .where(Vendor.category == category)
        .where(Vendor.event_types.any(event_type))
        .where(Vendor.city.ilike(f"%{city}%"))
    )

    result = await db.execute(q)
    vendors = result.scalars().all()

    if not vendors:
        return None

    def effective_cost(v: Vendor) -> float:
        if v.price_per_guest and guest_count:
            return v.price_per_guest * guest_count

        return (
            v.base_price
            if v.base_price > 0
            else float("inf")
        )

    cheapest = min(
        vendors,
        key=effective_cost,
    )

    evidence = make_evidence(
        session_id="feasibility",
        source_type="vendor_sql",
        source_ref=cheapest.id,
        content=(
            f"Cheapest {category}: "
            f"{cheapest.name} at "
            f"INR{effective_cost(cheapest):,.0f}"
        ),
        score=1.0,
        query=f"cheapest {category} in {city} for {event_type}",
    )

    return VendorResult(
        vendor_id=cheapest.id,
        name=cheapest.name,
        category=cheapest.category,
        city=cheapest.city,
        base_price=cheapest.base_price,
        price_per_guest=cheapest.price_per_guest,
        price_floor=cheapest.price_floor,
        min_capacity=cheapest.min_capacity,
        max_capacity=cheapest.max_capacity,
        rating=cheapest.rating,
        tags=cheapest.tags or [],
        description=cheapest.description,
        is_available=True,
        evidence=evidence,
    )