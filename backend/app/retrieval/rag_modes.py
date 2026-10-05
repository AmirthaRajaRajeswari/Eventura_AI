"""
Three RAG mode implementations for Eventura AI.

Mode 0 — NONE:    No retrieval. LLM answers from parametric knowledge only.
Mode 1 — BASIC:   Fixed top-k retrieval (vendor SQL + pgvector knowledge).
Mode 2 — AGENTIC: Dynamic retrieval with source routing, query refinement,
                  and sufficiency checking. Used by the ResearchAgent node.

The agentic mode is the core demonstration of Agentic RAG.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.retrieval.evidence import Evidence
from app.retrieval.knowledge_retrieval import retrieve_knowledge
from app.retrieval.vendor_retrieval import VendorResult, retrieve_vendors

logger = get_logger(__name__)

# ── Shared result type ────────────────────────────────────────────────────────

@dataclass
class RetrievalResult:
    """Unified result from any RAG mode."""
    vendors: list[VendorResult]
    knowledge: list[dict]         # knowledge chunk dicts with evidence
    all_evidence: list[Evidence]  # all evidence objects (for state)
    retrieval_rounds: int         # how many rounds were performed
    source_routing: list[str]     # which sources were queried
    queries_used: list[str]       # all queries executed
    sufficient: bool              # did the agent consider evidence sufficient?
    sufficiency_notes: str        # why it's sufficient or not

    @property
    def evidence_dicts(self) -> list[dict]:
        return [e.to_dict() for e in self.all_evidence]


# ── Mode 0: No RAG ────────────────────────────────────────────────────────────

async def retrieve_none(
    session_id: str,
    requirements: dict,
) -> RetrievalResult:
    """
    No retrieval baseline.
    Returns empty evidence — the LLM must answer from its own knowledge.
    Used to demonstrate hallucination risk without grounding.
    """
    logger.info("RAG mode: NONE — no retrieval performed", session_id=session_id)
    return RetrievalResult(
        vendors=[],
        knowledge=[],
        all_evidence=[],
        retrieval_rounds=0,
        source_routing=["none"],
        queries_used=[],
        sufficient=False,
        sufficiency_notes=(
            "No retrieval performed (baseline mode). "
            "LLM is answering from parametric knowledge only."
        ),
    )


# ── Mode 1: Basic RAG ─────────────────────────────────────────────────────────

async def retrieve_basic(
    db: AsyncSession,
    session_id: str,
    requirements: dict,
    information_need: dict,
) -> RetrievalResult:
    """
    Basic RAG: fixed top-k retrieval from both SQL and pgvector.
    No dynamic query refinement, no sufficiency check.
    Used as a baseline to compare against agentic retrieval.

    information_need:
        {
            "category": "venue",
            "description": "Wedding venue in Chennai for 500 guests",
            "constraints": {"city": "Chennai", "min_capacity": 500, ...}
        }
    """
    logger.info("RAG mode: BASIC", session_id=session_id, need=information_need.get("category"))

    event_type = requirements.get("event_type", "wedding")
    city = requirements.get("city", "")
    guest_count = requirements.get("guest_count")
    date = requirements.get("date")
    category = information_need.get("category", "venue")
    description = information_need.get("description", "")
    constraints = information_need.get("constraints", {})

    all_vendors: list[VendorResult] = []
    all_knowledge: list[dict] = []
    all_evidence: list[Evidence] = []
    queries_used: list[str] = []

    # Fixed vendor SQL retrieval
    vendor_query = f"{category} in {city} for {event_type}"
    queries_used.append(vendor_query)

    vendors = await retrieve_vendors(
        db=db,
        session_id=session_id,
        category=category,
        event_type=event_type,
        city=city,
        date=date,
        min_capacity=guest_count,
        max_price=constraints.get("max_price"),
        retrieval_round=0,
        limit=5,
    )
    all_vendors.extend(vendors)
    all_evidence.extend(v.evidence for v in vendors)

    # Fixed knowledge retrieval
    knowledge_query = f"{event_type} {category} planning requirements {city}"
    queries_used.append(knowledge_query)

    knowledge = await retrieve_knowledge(
        db=db,
        session_id=session_id,
        query=knowledge_query,
        event_types=[event_type, "general"],
        top_k=3,
        retrieval_round=0,
    )
    all_knowledge.extend(knowledge)
    all_evidence.extend(k["evidence"] for k in knowledge)

    return RetrievalResult(
        vendors=all_vendors,
        knowledge=all_knowledge,
        all_evidence=all_evidence,
        retrieval_rounds=1,
        source_routing=["vendor_sql", "knowledge_pgvector"],
        queries_used=queries_used,
        sufficient=True,  # basic mode always declares sufficient (no check)
        sufficiency_notes="Basic RAG: fixed top-k retrieval completed.",
    )


# ── Mode 2: Agentic RAG ───────────────────────────────────────────────────────

async def retrieve_agentic(
    db: AsyncSession,
    session_id: str,
    requirements: dict,
    information_need: dict,
    retrieval_round: int = 0,
    existing_evidence: list[Evidence] | None = None,
    llm: Any = None,
    rejected_vendor_ids: list[str] | None = None,
) -> RetrievalResult:
    """
    Agentic RAG: dynamic source routing, query construction, and
    sufficiency checking.

    The agent:
    1. Routes to the right source (vendor SQL vs. knowledge pgvector)
    2. Constructs targeted queries from structured constraints
    3. Checks if retrieved evidence is sufficient
    4. Re-retrieves with refined queries if needed (max 2 rounds)

    This is the primary demonstration of Agentic RAG capability.
    """
    logger.info(
        "RAG mode: AGENTIC",
        session_id=session_id,
        category=information_need.get("category"),
        round=retrieval_round,
    )

    existing_evidence = existing_evidence or []
    rejected_vendor_ids = rejected_vendor_ids or []
    all_vendors: list[VendorResult] = []
    all_knowledge: list[dict] = []
    all_evidence: list[Evidence] = list(existing_evidence)
    queries_used: list[str] = []
    source_routing: list[str] = []

    event_type = requirements.get("event_type", "wedding")
    city = requirements.get("city", "")
    guest_count = requirements.get("guest_count")
    date = requirements.get("date")
    category = information_need.get("category", "venue")
    constraints = information_need.get("constraints", {})
    description = information_need.get("description", "")

    # ── Step 1: Route to sources ───────────────────────────────────────────
    use_vendor_sql = _needs_vendor_data(category)
    use_knowledge = _needs_knowledge(category, event_type)

    if use_vendor_sql:
        source_routing.append("vendor_sql")
    if use_knowledge:
        source_routing.append("knowledge_pgvector")

    # ── Step 2: Construct targeted SQL query ───────────────────────────────
    if use_vendor_sql:
        max_price = _derive_max_price(category, requirements, constraints)
        min_cap = guest_count if category in ("venue", "catering") else None

        vendor_query = _build_vendor_query(category, city, event_type, date, constraints)
        queries_used.append(vendor_query)

        vendors = await retrieve_vendors(
            db=db,
            session_id=session_id,
            category=category,
            event_type=event_type,
            city=city,
            date=date,
            min_capacity=min_cap,
            max_price=max_price,
            retrieval_round=retrieval_round,
            rejected_vendor_ids=rejected_vendor_ids,
            limit=8,
        )
        all_vendors.extend(vendors)
        all_evidence.extend(v.evidence for v in vendors)

    # ── Step 3: Construct targeted knowledge query ─────────────────────────
    if use_knowledge:
        knowledge_query = _build_knowledge_query(
            category, event_type, description, requirements
        )
        queries_used.append(knowledge_query)

        knowledge = await retrieve_knowledge(
            db=db,
            session_id=session_id,
            query=knowledge_query,
            event_types=[event_type, "general"],
            top_k=4,
            retrieval_round=retrieval_round,
        )
        all_knowledge.extend(knowledge)
        all_evidence.extend(k["evidence"] for k in knowledge)

    # ── Step 4: Sufficiency check ──────────────────────────────────────────
    sufficient, notes = _check_sufficiency(
        category=category,
        vendors=all_vendors,
        knowledge=all_knowledge,
        requirements=requirements,
        constraints=constraints,
        retrieval_round=retrieval_round,
    )

    # ── Step 5: Re-retrieve if insufficient (max 2 rounds) ─────────────────
    if not sufficient and retrieval_round < 2:
        logger.info(
            "Agentic RAG: evidence insufficient, re-retrieving",
            session_id=session_id,
            round=retrieval_round + 1,
            reason=notes,
        )

        refined_query = _refine_query(
            category=category,
            event_type=event_type,
            city=city,
            constraints=constraints,
            insufficiency_reason=notes,
            previous_vendors=all_vendors,
        )
        queries_used.append(refined_query)

        if use_vendor_sql:
            # Retry with relaxed constraints
            refined_vendors = await retrieve_vendors(
                db=db,
                session_id=session_id,
                category=category,
                event_type=event_type,
                city=city,
                date=date,
                min_capacity=None,  # relax capacity constraint
                max_price=None,     # relax price constraint
                rejected_vendor_ids=rejected_vendor_ids,
                retrieval_round=retrieval_round + 1,
                limit=5,
            )
            # Deduplicate
            existing_ids = {v.vendor_id for v in all_vendors}
            new_vendors = [v for v in refined_vendors if v.vendor_id not in existing_ids]
            all_vendors.extend(new_vendors)
            all_evidence.extend(v.evidence for v in new_vendors)

        if use_knowledge:
            refined_knowledge = await retrieve_knowledge(
                db=db,
                session_id=session_id,
                query=refined_query,
                event_types=[event_type, "general"],
                top_k=3,
                retrieval_round=retrieval_round + 1,
            )
            existing_doc_ids = {k["document_id"] + str(k.get("chunk_index", 0)) for k in all_knowledge}
            new_knowledge = [
                k for k in refined_knowledge
                if k["document_id"] + str(k.get("chunk_index", 0)) not in existing_doc_ids
            ]
            all_knowledge.extend(new_knowledge)
            all_evidence.extend(k["evidence"] for k in new_knowledge)

        # Re-check sufficiency after refinement
        sufficient, notes = _check_sufficiency(
            category=category,
            vendors=all_vendors,
            knowledge=all_knowledge,
            requirements=requirements,
            constraints=constraints,
            retrieval_round=retrieval_round + 1,
        )
        retrieval_round += 1

    total_rounds = retrieval_round + 1
    logger.info(
        "Agentic RAG complete",
        session_id=session_id,
        vendors=len(all_vendors),
        knowledge_chunks=len(all_knowledge),
        rounds=total_rounds,
        sufficient=sufficient,
    )

    return RetrievalResult(
        vendors=all_vendors,
        knowledge=all_knowledge,
        all_evidence=all_evidence,
        retrieval_rounds=total_rounds,
        source_routing=source_routing,
        queries_used=queries_used,
        sufficient=sufficient,
        sufficiency_notes=notes,
    )


# ── Source routing helpers ────────────────────────────────────────────────────

# Categories that need structured vendor data from SQL
_VENDOR_CATEGORIES = {
    "venue", "catering", "decoration", "photography", "makeup",
    "music", "ritual_services", "transport", "cake", "entertainer",
    "sound_lights", "stage", "permissions_security", "performers",
    "banners_printing",
}

# Categories where knowledge docs are especially useful
_KNOWLEDGE_CATEGORIES = {
    "venue", "catering", "ritual_services", "permissions_security",
    "general",
}


def _needs_vendor_data(category: str) -> bool:
    return category in _VENDOR_CATEGORIES


def _needs_knowledge(category: str, event_type: str) -> bool:
    # Always retrieve knowledge for first-round planning
    return category in _KNOWLEDGE_CATEGORIES or event_type in ("wedding",)


def _build_vendor_query(
    category: str,
    city: str,
    event_type: str,
    date: str | None,
    constraints: dict,
) -> str:
    parts = [f"{category}", f"city={city}", f"event={event_type}"]
    if date:
        parts.append(f"date={date}")
    if constraints.get("min_capacity"):
        parts.append(f"capacity>={constraints['min_capacity']}")
    if constraints.get("max_price"):
        parts.append(f"price<={constraints['max_price']}")
    return " ".join(parts)


def _build_knowledge_query(
    category: str,
    event_type: str,
    description: str,
    requirements: dict,
) -> str:
    city = requirements.get("city", "")
    themes = requirements.get("preferences", {}).get("themes", [])
    theme_str = " ".join(themes) if themes else ""
    return f"{event_type} {category} planning requirements {theme_str} {city}".strip()


def _derive_max_price(
    category: str,
    requirements: dict,
    constraints: dict,
) -> float | None:
    """
    Derive a reasonable max price for a category from the total budget.
    Uses deterministic budget allocation ratios — no LLM arithmetic.
    """
    budget = requirements.get("budget")
    if not budget:
        return constraints.get("max_price")

    # Approximate allocation ratios by category
    RATIOS: dict[str, float] = {
        "venue": 0.32,
        "catering": 0.38,
        "decoration": 0.13,
        "photography": 0.12,
        "makeup": 0.07,
        "music": 0.06,
        "ritual_services": 0.04,
        "transport": 0.04,
        "cake": 0.04,
        "entertainer": 0.05,
        "sound_lights": 0.20,
        "stage": 0.15,
        "permissions_security": 0.05,
        "performers": 0.25,
        "banners_printing": 0.05,
    }
    ratio = RATIOS.get(category, 0.15)
    # Add 30% buffer so we don't filter out slightly over-budget options
    return round(budget * ratio * 1.30, -3)


# ── Sufficiency checking ──────────────────────────────────────────────────────

def _check_sufficiency(
    category: str,
    vendors: list[VendorResult],
    knowledge: list[dict],
    requirements: dict,
    constraints: dict,
    retrieval_round: int,
) -> tuple[bool, str]:
    """
    Deterministically check whether retrieved evidence is sufficient.

    Returns (is_sufficient, explanation_string).
    """
    issues = []

    # Need at least 1 vendor option
    if _needs_vendor_data(category) and len(vendors) == 0:
        issues.append(f"No {category} vendors found in {requirements.get('city', 'requested city')}")

    # Availability check for venue/catering
    if category in ("venue", "catering") and requirements.get("date"):
        available = [v for v in vendors if v.is_available]
        if len(vendors) > 0 and len(available) == 0:
            issues.append(
                f"Found {len(vendors)} {category} vendors but none available on "
                f"{requirements.get('date')}"
            )

    # Capacity check for venue
    if category == "venue":
        guest_count = requirements.get("guest_count")
        if guest_count:
            capacity_ok = [
                v for v in vendors
                if v.max_capacity is None or v.max_capacity >= guest_count
            ]
            if len(vendors) > 0 and len(capacity_ok) == 0:
                issues.append(
                    f"No venue found with capacity >= {guest_count} guests"
                )

    if issues:
        return False, "; ".join(issues)

    return True, f"Retrieved {len(vendors)} vendors and {len(knowledge)} knowledge chunks."


def _refine_query(
    category: str,
    event_type: str,
    city: str,
    constraints: dict,
    insufficiency_reason: str,
    previous_vendors: list[VendorResult],
) -> str:
    """
    Generate a refined retrieval query based on why the previous attempt failed.
    This is deterministic query construction — not LLM-generated.
    """
    # If capacity was the issue, broaden the search
    if "capacity" in insufficiency_reason.lower():
        return f"{category} {city} {event_type} large capacity high capacity"

    # If no vendors found, try neighbouring cities or relax filters
    if "no" in insufficiency_reason.lower() and "vendor" in insufficiency_reason.lower():
        return f"{category} {event_type} india alternatives budget options"

    # If availability was the issue, look for alternatives
    if "available" in insufficiency_reason.lower():
        return f"{category} {city} {event_type} alternative available backup"

    # Default refinement
    return f"{category} {event_type} {city} planning guide requirements best practices"
