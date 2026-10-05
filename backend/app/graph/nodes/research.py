"""
Research Agent — Eventura AI (Agentic RAG core)

Responsibilities:
  - Receive information needs from the Planner
  - Route each need to the correct source (SQL vs pgvector)
  - Execute retrieval with appropriate queries
  - Assess evidence sufficiency
  - Re-retrieve if insufficient (max 2 rounds)
  - Populate vendor_selections with retrieved vendors + evidence IDs
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.graph.activity import emit_activity
from app.graph.state import EventState, VendorSelection
from app.logger import get_logger
from app.retrieval.evidence import Evidence
from app.retrieval.interface import retrieve
from app.retrieval.rag_modes import RetrievalResult

logger = get_logger(__name__)


async def research_node(
    state: EventState,
    config: RunnableConfig,
) -> dict:
    """
    LangGraph node: Research Agent.

    Executes retrieval for all information needs from the Planner.
    """

    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")
    rag_mode = state.get("rag_mode", "agentic")
    req = state.get("requirements", {})
    information_needs = state.get("information_needs", [])

    await emit_activity(
        session_id=session_id,
        agent="ResearchAgent",
        action="start_retrieval",
        status="running",
        detail=(
            f"Mode={rag_mode.upper()} | "
            f"{len(information_needs)} information needs"
        ),
        db=db,
    )

    if not information_needs:
        await emit_activity(
            session_id=session_id,
            agent="ResearchAgent",
            action="start_retrieval",
            status="error",
            detail="No information needs received from Planner",
            db=db,
        )

        return {
            "errors": state.get("errors", [])
            + ["ResearchAgent: No information needs"]
        }

    # ------------------------------------------------------------------
    # Existing state
    # ------------------------------------------------------------------
    all_evidence: list[dict] = list(
        state.get("evidence", [])
    )

    all_evidence_objs: list[Evidence] = []

    vendor_selections: list[VendorSelection] = list(
        state.get("vendor_selections", [])
    )

    # Vendors explicitly rejected by Critic/Planner.
    rejected_ids = set(
        state.get("rejected_vendor_ids", [])
    )

    logger.info(
        "ResearchAgent vendor constraints",
        rejected_vendor_ids=list(rejected_ids),
    )

    # ------------------------------------------------------------------
    # Handle replanning
    # ------------------------------------------------------------------

    # Disruption replan:
    # remove selections belonging to affected categories.
    if state.get("disruption_type"):
        replan_categories = set(
            state.get("replan_categories", [])
        )

        vendor_selections = [
            selection
            for selection in vendor_selections
            if selection.get("category")
            not in replan_categories
        ]

        logger.info(
            "ResearchAgent disruption replan",
            removed_categories=list(replan_categories),
        )

    # Critic-driven replan:
    #
    # IMPORTANT:
    # Remove ALL selections for categories being replanned.
    # The category must be rebuilt from fresh retrieval results.
    elif state.get("critic_feedback"):
        planned_categories = {
            need.get("category")
            for need in information_needs
            if need.get("category")
        }

        old_count = len(vendor_selections)

        vendor_selections = [
            selection
            for selection in vendor_selections
            if (
                selection.get("category")
                not in planned_categories
                and selection.get("vendor_id")
                not in rejected_ids
            )
        ]

        logger.info(
            "ResearchAgent critic replan",
            removed_previous_selections=old_count - len(vendor_selections),
            planned_categories=list(planned_categories),
            rejected_vendor_ids=list(rejected_ids),
        )

    total_retrieval_rounds = state.get(
        "retrieval_rounds",
        0,
    )

    # ------------------------------------------------------------------
    # Retrieve for each information need
    # ------------------------------------------------------------------
    for need in information_needs:
        category = need.get("category", "")

        await emit_activity(
            session_id=session_id,
            agent="ResearchAgent",
            action="retrieve",
            status="running",
            detail=(
                f"Retrieving {category} "
                f"({rag_mode.upper()})…"
            ),
            db=db,
        )

        result: RetrievalResult = await retrieve(
            db=db,
            session_id=session_id,
            rag_mode=rag_mode,
            requirements=req,
            information_need=need,
            retrieval_round=0,
            existing_evidence=all_evidence_objs,
            rejected_vendor_ids=list(rejected_ids),
        )

        total_retrieval_rounds = max(
            total_retrieval_rounds,
            result.retrieval_rounds,
        )

        # ------------------------------------------------------------------
        # Collect evidence
        # ------------------------------------------------------------------
        for ev in result.all_evidence:
            if not any(
                e.get("evidence_id") == ev.evidence_id
                for e in all_evidence
            ):
                all_evidence.append(
                    ev.to_dict()
                )
                all_evidence_objs.append(ev)

        await emit_activity(
            session_id=session_id,
            agent="ResearchAgent",
            action="retrieve",
            status="success",
            detail=(
                f"Retrieved {len(result.vendors)} "
                f"{category} vendors, "
                f"{len(result.knowledge)} knowledge chunks "
                f"({result.retrieval_rounds} round(s)) — "
                + (
                    "sufficient ✓"
                    if result.sufficient
                    else "insufficient ⚠"
                )
            ),
            payload={
                "category": category,
                "vendors_found": len(result.vendors),
                "knowledge_chunks": len(result.knowledge),
                "rounds": result.retrieval_rounds,
                "sufficient": result.sufficient,
                "sources": result.source_routing,
            },
            db=db,
        )

        # ------------------------------------------------------------------
        # Remove rejected vendors BEFORE selection.
        #
        # This is the important safety boundary:
        # a vendor rejected by Critic must never become the new selection.
        # ------------------------------------------------------------------
        available_vendors = [
            vendor
            for vendor in result.vendors
            if vendor.vendor_id not in rejected_ids
        ]

        rejected_from_results = [
            vendor.vendor_id
            for vendor in result.vendors
            if vendor.vendor_id in rejected_ids
        ]

        if rejected_from_results:
            logger.info(
                "ResearchAgent filtered rejected vendors",
                category=category,
                filtered_vendor_ids=rejected_from_results,
            )

        # ------------------------------------------------------------------
        # Select best vendor
        # ------------------------------------------------------------------
        if available_vendors:
            best = _select_best_vendor(
                available_vendors,
                need,
                req,
            )

            selection: VendorSelection = {
                "vendor_id": best.vendor_id,
                "name": best.name,
                "category": category,
                "city": best.city,
                "base_price": best.base_price,
                "price_per_guest": best.price_per_guest,
                "price_floor": best.price_floor,
                "quoted_price": best.estimated_price(
                    req.get("guest_count"),
                    req.get("duration_days", 1),
                ),
                "final_price": None,
                "evidence_ids": [
                    best.evidence.evidence_id
                ],
                "negotiation_savings": 0.0,
                "critic_warnings": [],
                "status": "selected",
            }

            # --------------------------------------------------------------
            # Replace any existing selection for this category.
            # --------------------------------------------------------------
            existing_idx = next(
                (
                    i
                    for i, existing in enumerate(
                        vendor_selections
                    )
                    if existing.get("category") == category
                ),
                None,
            )

            if existing_idx is not None:
                vendor_selections[
                    existing_idx
                ] = selection
            else:
                vendor_selections.append(
                    selection
                )

            await emit_activity(
                session_id=session_id,
                agent="ResearchAgent",
                action="select_vendor",
                status="success",
                detail=(
                    f"Selected: {best.name} "
                    f"for {category} "
                    f"@ ₹{selection['quoted_price']:,.0f} "
                    f"[{best.evidence.evidence_id}]"
                ),
                db=db,
            )

        else:
            # --------------------------------------------------------------
            # No acceptable vendor after rejected-vendor filtering.
            # --------------------------------------------------------------
            await emit_activity(
                session_id=session_id,
                agent="ResearchAgent",
                action="select_vendor",
                status=(
                    "error"
                    if need.get("priority") == "mandatory"
                    else "warning"
                ),
                detail=(
                    f"No suitable {category} vendor found "
                    f"after excluding rejected vendors"
                ),
                db=db,
            )

    # ------------------------------------------------------------------
    # Final safety filter
    #
    # Never allow a rejected vendor to leave this node as a selection.
    # ------------------------------------------------------------------
    vendor_selections = [
        selection
        for selection in vendor_selections
        if selection.get("vendor_id")
        not in rejected_ids
    ]

    await emit_activity(
        session_id=session_id,
        agent="ResearchAgent",
        action="retrieval_complete",
        status="success",
        detail=(
            f"Retrieval complete: "
            f"{len(vendor_selections)} vendors selected, "
            f"{len(all_evidence)} evidence items, "
            f"{total_retrieval_rounds} total rounds"
        ),
        db=db,
    )

    return {
        "vendor_selections": vendor_selections,
        "evidence": all_evidence,
        "retrieval_rounds": total_retrieval_rounds,
        "status": "budgeting",
    }


def _select_best_vendor(
    vendors: list,
    need: dict,
    req: dict,
) -> object:
    """
    Select the best vendor for a category.

    Strategy:
    - Prefer available vendors
    - Prefer vendors within budget allocation
    - Among those, prefer highest rating
    """

    guest_count = req.get("guest_count")
    duration_days = req.get(
        "duration_days",
        1,
    )

    max_price = need.get(
        "constraints",
        {},
    ).get("max_price")

    def score(vendor) -> tuple:
        price = vendor.estimated_price(
            guest_count,
            duration_days,
        )

        within_budget = (
            1
            if (
                max_price is None
                or price <= max_price
            )
            else 0
        )

        return (
            vendor.is_available,
            within_budget,
            vendor.rating,
        )

    return max(
        vendors,
        key=score,
    )