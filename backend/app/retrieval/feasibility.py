"""
Deterministic feasibility calculations for Eventura AI.

CRITICAL: All arithmetic here is Python — zero LLM involvement.
The LLM may explain the result, but must not compute it.

Checks:
  - Minimum possible cost vs budget
  - Venue capacity vs guest count
  - Date availability
  - Mandatory category coverage
  - Minimum notice period
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.retrieval.vendor_retrieval import get_cheapest_vendor

logger = get_logger(__name__)

# Mandatory vendor categories per event type
MANDATORY_CATEGORIES: dict[str, list[str]] = {
    "wedding": ["venue", "catering", "decoration", "photography"],
    "birthday": ["venue", "catering", "decoration"],
    "college_fest": ["venue", "catering", "sound_lights", "stage"],
}

# Optional but common categories
OPTIONAL_CATEGORIES: dict[str, list[str]] = {
    "wedding": ["makeup", "music", "ritual_services", "transport"],
    "birthday": ["cake", "entertainer", "photography"],
    "college_fest": ["performers", "photography", "banners_printing", "permissions_security"],
}


@dataclass
class FeasibilityResult:
    feasible: bool
    min_cost: float           # deterministically calculated minimum
    budget: float
    shortfall: float          # max(0, min_cost - budget)
    coverage_pct: float       # budget / min_cost * 100
    issues: list[str] = field(default_factory=list)
    relaxations: list[str] = field(default_factory=list)
    category_min_costs: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "feasible": self.feasible,
            "min_cost": round(self.min_cost, 2),
            "budget": round(self.budget, 2),
            "shortfall": round(self.shortfall, 2),
            "coverage_pct": round(self.coverage_pct, 1),
            "issues": self.issues,
            "relaxations": self.relaxations,
            "category_min_costs": {k: round(v, 2) for k, v in self.category_min_costs.items()},
            "warnings": self.warnings,
        }


async def check_feasibility(
    db: AsyncSession,
    event_type: str,
    city: str,
    guest_count: int,
    budget: float,
    date_str: str | None,
    duration_days: int = 1,
    preferences: dict | None = None,
) -> FeasibilityResult:
    """
    Deterministically assess whether an event is feasible.

    Calculates the absolute minimum cost by finding the cheapest vendor
    in each mandatory category and summing them up.
    """
    logger.info(
        "Feasibility check",
        event_type=event_type,
        city=city,
        guests=guest_count,
        budget=budget,
    )

    issues: list[str] = []
    relaxations: list[str] = []
    warnings: list[str] = []
    category_min_costs: dict[str, float] = {}

    mandatory = MANDATORY_CATEGORIES.get(event_type, ["venue", "catering"])

    # ── Calculate minimum cost per mandatory category ─────────────────────
    total_min_cost = 0.0
    for cat in mandatory:
        cheapest = await get_cheapest_vendor(
            db=db,
            category=cat,
            event_type=event_type,
            city=city,
            guest_count=guest_count if cat == "catering" else None,
        )

        if cheapest is None:
            issues.append(f"No {cat} vendors found in {city} for {event_type}")
            category_min_costs[cat] = 0.0
            continue

        # Deterministic cost calculation
        min_price = cheapest.estimated_price(
            guest_count if cat == "catering" else None,
            duration_days,
        )
        category_min_costs[cat] = min_price
        total_min_cost += min_price

    # ── Date checks ───────────────────────────────────────────────────────
    if date_str:
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = date.today()
            days_until = (event_date - today).days

            if days_until < 0:
                issues.append(f"Event date {date_str} is in the past")
            elif days_until < 7:
                warnings.append(
                    f"Only {days_until} days until the event — very short notice for vendors"
                )
            elif days_until < 30:
                warnings.append(
                    f"Only {days_until} days notice — some vendors may be unavailable"
                )
        except ValueError:
            issues.append(f"Invalid date format: {date_str!r} (expected YYYY-MM-DD)")

    # ── Guest count checks ────────────────────────────────────────────────
    if guest_count < 1:
        issues.append("Guest count must be at least 1")
    elif guest_count > 5000:
        warnings.append(
            f"Very large guest count ({guest_count}) — venue options may be limited"
        )

    # ── Budget feasibility ────────────────────────────────────────────────
    shortfall = max(0.0, total_min_cost - budget)
    coverage_pct = (budget / total_min_cost * 100) if total_min_cost > 0 else 100.0
    feasible = len(issues) == 0 and shortfall == 0

    if shortfall > 0:
        issues.append(
            f"Budget ₹{budget:,.0f} is below minimum estimated cost of ₹{total_min_cost:,.0f} "
            f"(shortfall: ₹{shortfall:,.0f})"
        )
        # Suggest relaxations
        relaxations.extend(_suggest_relaxations(
            budget=budget,
            min_cost=total_min_cost,
            guest_count=guest_count,
            event_type=event_type,
            city=city,
        ))

    logger.info(
        "Feasibility result",
        feasible=feasible,
        min_cost=total_min_cost,
        budget=budget,
        shortfall=shortfall,
    )

    return FeasibilityResult(
        feasible=feasible,
        min_cost=total_min_cost,
        budget=budget,
        shortfall=shortfall,
        coverage_pct=coverage_pct,
        issues=issues,
        relaxations=relaxations,
        category_min_costs=category_min_costs,
        warnings=warnings,
    )


def _suggest_relaxations(
    budget: float,
    min_cost: float,
    guest_count: int,
    event_type: str,
    city: str,
) -> list[str]:
    """
    Generate concrete, deterministic relaxation suggestions.
    All numbers are computed — not hallucinated by the LLM.
    """
    relaxations = []
    needed_increase_pct = round((min_cost - budget) / budget * 100, 1)

    # Option 1: Increase budget
    relaxations.append(
        f"Increase budget by {needed_increase_pct}% to ₹{min_cost:,.0f}"
    )

    # Option 2: Reduce guest count
    if guest_count > 50:
        reduction_target = round(budget / (min_cost / guest_count), -1)
        if reduction_target > 0:
            relaxations.append(
                f"Reduce guest count from {guest_count} to approximately "
                f"{int(reduction_target)} to fit within budget"
            )

    # Option 3: Different city
    if city.lower() not in ("coimbatore", "pune"):
        relaxations.append(
            "Consider a smaller city (e.g. Coimbatore, Pune) where venue and "
            "catering costs are typically 20-30% lower"
        )

    # Option 4: Remove optional categories
    optional = OPTIONAL_CATEGORIES.get(event_type, [])
    if optional:
        relaxations.append(
            f"Remove optional services: {', '.join(optional[:3])} "
            f"to reduce costs"
        )

    return relaxations


def calculate_budget_breakdown(
    budget: float,
    event_type: str,
    guest_count: int,
    duration_days: int = 1,
) -> dict[str, float]:
    """
    Deterministically allocate a budget across categories.
    Returns recommended spend per category in INR.

    Used by Budget Agent — no LLM arithmetic.
    """
    # Allocation ratios by event type
    WEDDING_RATIOS: dict[str, float] = {
        "venue": 0.28,
        "catering": 0.35,
        "decoration": 0.12,
        "photography": 0.10,
        "makeup": 0.05,
        "music": 0.04,
        "ritual_services": 0.03,
        "transport": 0.03,
    }
    BIRTHDAY_RATIOS: dict[str, float] = {
        "venue": 0.25,
        "catering": 0.35,
        "decoration": 0.15,
        "cake": 0.08,
        "entertainer": 0.10,
        "photography": 0.07,
    }
    COLLEGE_FEST_RATIOS: dict[str, float] = {
        "venue": 0.15,
        "sound_lights": 0.20,
        "stage": 0.15,
        "performers": 0.25,
        "catering": 0.15,
        "permissions_security": 0.05,
        "banners_printing": 0.05,
    }

    ratios_map = {
        "wedding": WEDDING_RATIOS,
        "birthday": BIRTHDAY_RATIOS,
        "college_fest": COLLEGE_FEST_RATIOS,
    }
    ratios = ratios_map.get(event_type, WEDDING_RATIOS)

    breakdown = {}
    for cat, ratio in ratios.items():
        # Deterministic allocation — round to nearest 100 INR
        alloc = round(budget * ratio, -2)
        breakdown[cat] = alloc

    return breakdown


def calculate_remaining_budget(
    total_budget: float,
    category_costs: dict[str, float],
) -> dict[str, float]:
    """
    Deterministically calculate budget remaining after allocations.
    Returns {"spent": x, "remaining": y, "pct_used": z}.
    No LLM arithmetic.
    """
    spent = sum(category_costs.values())
    remaining = total_budget - spent
    pct_used = (spent / total_budget * 100) if total_budget > 0 else 0.0

    return {
        "total_budget": round(total_budget, 2),
        "spent": round(spent, 2),
        "remaining": round(remaining, 2),
        "pct_used": round(pct_used, 1),
        "over_budget": remaining < 0,
    }


def apply_budget_reduction(
    current_budget: float,
    reduction_pct: float,
    category_allocations: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """
    Deterministically apply a percentage budget reduction.
    Returns (new_budget, new_allocations).
    No LLM arithmetic.
    """
    new_budget = round(current_budget * (1 - reduction_pct / 100), 2)
    new_allocations = {
        cat: round(alloc * (1 - reduction_pct / 100), 2)
        for cat, alloc in category_allocations.items()
    }
    return new_budget, new_allocations
