"""
Negotiator Agent — Eventura AI

Negotiation is ONLY for catering (MVP).
Maximum 2 rounds: Offer → Counter → Final.

The vendor-side response is rule-based (deterministic) via the mock vendor API.
The LLM only phrases the negotiation messages — it does NOT decide price floors.

Structure:
  Round 1: We offer (quoted_price * discount_factor)
  Round 2: If vendor counters, we accept if within budget, else push harder
"""

from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.messages import HumanMessage

from app.graph.activity import emit_activity
from app.graph.state import EventState, NegotiationLog, NegotiationRound
from app.llm.base import get_llm
from app.logger import get_logger
from app.mock_vendors.client import negotiate

logger = get_logger(__name__)

NEGOTIATION_CATEGORIES = {"catering"}
NEGOTIATION_DISCOUNT_ROUND1 = 0.12   # offer 12% below quoted
NEGOTIATION_DISCOUNT_ROUND2 = 0.06   # if countered, offer 6% below quoted


async def negotiator_node(state: EventState, config: RunnableConfig) -> dict:
    """
    LangGraph node: Negotiator Agent.
    Negotiates with catering vendors via the mock vendor API.
    """
    session_id = state["session_id"]
    db = config.get("configurable", {}).get("db")
    req = state.get("requirements", {})
    vendor_selections = state.get("vendor_selections", [])
    negotiation_logs: list[NegotiationLog] = list(state.get("negotiation_logs", []))

    # Find catering selections eligible for negotiation
    catering_selections = [
        sel for sel in vendor_selections
        if sel.get("category") in NEGOTIATION_CATEGORIES
        and sel.get("status") not in ("booked", "confirmed")
    ]

    if not catering_selections:
        await emit_activity(
            session_id=session_id,
            agent="NegotiatorAgent",
            action="negotiate",
            status="success",
            detail="No catering vendors to negotiate with — skipping",
            db=db,
        )
        return {"status": "reviewing"}

    updated_selections = list(vendor_selections)

    for sel in catering_selections:
        vendor_id = sel.get("vendor_id", "")
        category = sel.get("category", "catering")
        quoted_price = sel.get("quoted_price", 0.0)
        price_floor = sel.get("price_floor", quoted_price * 0.85)

        await emit_activity(
            session_id=session_id,
            agent="NegotiatorAgent",
            action="negotiate",
            status="running",
            detail=f"Negotiating with {sel.get('name')} — quoted ₹{quoted_price:,.0f}",
            db=db,
        )

        log: NegotiationLog = {
            "vendor_id": vendor_id,
            "category": category,
            "initial_price": quoted_price,
            "final_price": None,
            "savings": 0.0,
            "rounds": [],
            "status": "in_progress",
        }

        final_price = quoted_price  # default: no savings

        # ── Round 1 ────────────────────────────────────────────────────────
        offer_r1 = round(quoted_price * (1 - NEGOTIATION_DISCOUNT_ROUND1), -2)
        offer_message_r1 = await _phrase_offer(
            vendor_name=sel.get("name", ""),
            category=category,
            offer_price=offer_r1,
            quoted_price=quoted_price,
            round_number=1,
            llm_provider=state.get("llm_provider"),
        )

        await emit_activity(
            session_id=session_id,
            agent="NegotiatorAgent",
            action="send_offer",
            status="running",
            detail=f"Round 1 offer: ₹{offer_r1:,.0f} (quoted: ₹{quoted_price:,.0f})",
            db=db,
        )

        try:
            r1_response = await negotiate(
                vendor_id=vendor_id,
                session_id=session_id,
                offer_price=offer_r1,
                round_number=1,
                context=offer_message_r1,
            )
        except Exception as e:
            logger.warning("Negotiation round 1 failed", error=str(e))
            r1_response = {
                "vendor_response": "rejected",
                "counter_price": None,
                "final_price": None,
                "message": "Vendor unavailable",
            }

        round1: NegotiationRound = {
            "round_number": 1,
            "our_offer": offer_r1,
            "vendor_response": r1_response.get("vendor_response", "rejected"),
            "counter_price": r1_response.get("counter_price"),
            "final_price": r1_response.get("final_price"),
            "message": r1_response.get("message", ""),
            "timestamp": _now_iso(),
        }
        log["rounds"].append(round1)

        await emit_activity(
            session_id=session_id,
            agent="NegotiatorAgent",
            action="receive_response",
            status="success",
            detail=(
                f"Round 1 response: {r1_response.get('vendor_response')} "
                + (f"— counter ₹{r1_response.get('counter_price'):,.0f}"
                   if r1_response.get("counter_price") else "")
            ),
            db=db,
        )

        if r1_response.get("vendor_response") == "accepted":
            final_price = r1_response["final_price"] or offer_r1
            log["status"] = "accepted"

        elif r1_response.get("vendor_response") == "counter":
            counter_price = r1_response["counter_price"] or quoted_price

            # ── Round 2 ────────────────────────────────────────────────────
            offer_r2 = round(quoted_price * (1 - NEGOTIATION_DISCOUNT_ROUND2), -2)
            # Accept counter if it's better than our round-2 offer
            if counter_price <= offer_r2:
                final_price = counter_price
                r2_response = {
                    "vendor_response": "accepted",
                    "final_price": counter_price,
                    "message": "Counter accepted.",
                }
            else:
                offer_message_r2 = await _phrase_offer(
                    vendor_name=sel.get("name", ""),
                    category=category,
                    offer_price=offer_r2,
                    quoted_price=quoted_price,
                    round_number=2,
                    llm_provider=state.get("llm_provider"),
                )

                await emit_activity(
                    session_id=session_id,
                    agent="NegotiatorAgent",
                    action="send_offer",
                    status="running",
                    detail=f"Round 2 offer: ₹{offer_r2:,.0f}",
                    db=db,
                )

                try:
                    r2_response = await negotiate(
                        vendor_id=vendor_id,
                        session_id=session_id,
                        offer_price=offer_r2,
                        round_number=2,
                        context=offer_message_r2,
                    )
                except Exception as e:
                    logger.warning("Negotiation round 2 failed", error=str(e))
                    r2_response = {"vendor_response": "accepted", "final_price": offer_r2}

                final_price = r2_response.get("final_price") or offer_r2

            round2: NegotiationRound = {
                "round_number": 2,
                "our_offer": offer_r2,
                "vendor_response": r2_response.get("vendor_response", "accepted"),
                "counter_price": r2_response.get("counter_price"),
                "final_price": r2_response.get("final_price"),
                "message": r2_response.get("message", ""),
                "timestamp": _now_iso(),
            }
            log["rounds"].append(round2)
            log["status"] = "accepted"

            await emit_activity(
                session_id=session_id,
                agent="NegotiatorAgent",
                action="receive_response",
                status="success",
                detail=f"Round 2 response: {r2_response.get('vendor_response')} — ₹{final_price:,.0f}",
                db=db,
            )

        else:
            # Rejected both rounds — keep quoted price
            log["status"] = "rejected"
            final_price = quoted_price

        # ── Record savings ─────────────────────────────────────────────────
        savings = round(quoted_price - final_price, 2)
        log["final_price"] = round(final_price, 2)
        log["savings"] = max(0.0, savings)
        negotiation_logs.append(log)

        await emit_activity(
            session_id=session_id,
            agent="NegotiatorAgent",
            action="negotiation_complete",
            status="success",
            detail=(
                f"{sel.get('name')}: ₹{quoted_price:,.0f} → ₹{final_price:,.0f} "
                f"(saved ₹{max(0, savings):,.0f})"
            ),
            db=db,
        )

        # Update vendor selection with final price
        for i, s in enumerate(updated_selections):
            if s.get("vendor_id") == vendor_id:
                updated_selections[i] = {
                    **s,
                    "final_price": round(final_price, 2),
                    "negotiation_savings": max(0.0, savings),
                }

    return {
        "vendor_selections": updated_selections,
        "negotiation_logs": negotiation_logs,
        "status": "reviewing",
    }


async def _phrase_offer(
    vendor_name: str,
    category: str,
    offer_price: float,
    quoted_price: float,
    round_number: int,
    llm_provider: str | None,
) -> str:
    """LLM phrases the negotiation message. Prices are computed deterministically above."""
    prompt = (
        f"Write a brief, professional negotiation message to {vendor_name} "
        f"for {category} services. "
        f"Their quoted price is ₹{quoted_price:,.0f}. "
        f"We are offering ₹{offer_price:,.0f} (round {round_number}). "
        f"Keep it to 2 sentences, polite and business-like."
    )
    try:
        llm = get_llm(provider=llm_provider, temperature=0.4)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return resp.content.strip()
    except Exception:
        discount_pct = round((1 - offer_price / quoted_price) * 100, 1)
        return (
            f"We appreciate your quote of ₹{quoted_price:,.0f} for {category} services. "
            f"We would like to propose ₹{offer_price:,.0f} "
            f"({discount_pct}% below your quoted price)."
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


