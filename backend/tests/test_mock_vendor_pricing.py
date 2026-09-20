"""
Unit tests for deterministic mock vendor pricing and negotiation logic.

These tests verify that arithmetic is never delegated to the LLM.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.mock_vendors.router import _calculate_price, _negotiate_rules


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_vendor(
    base_price: float = 200_000.0,
    price_per_guest: float | None = None,
    price_floor: float = 160_000.0,
) -> MagicMock:
    v = MagicMock()
    v.base_price = base_price
    v.price_per_guest = price_per_guest
    v.price_floor = price_floor
    v.id = "VEN-TEST"
    return v


# ── Price calculation tests ───────────────────────────────────────────────────

class TestCalculatePrice:
    def test_base_price_single_day(self):
        vendor = make_vendor(base_price=200_000)
        total, breakdown = _calculate_price(vendor, guest_count=None, duration_days=1)
        assert total == 200_000.0
        assert breakdown["base_price"] == 200_000.0
        assert breakdown["total"] == 200_000.0

    def test_base_price_multi_day(self):
        vendor = make_vendor(base_price=200_000)
        total, breakdown = _calculate_price(vendor, guest_count=None, duration_days=2)
        # Day 2 is 70% of base
        expected_extra = round(200_000 * 0.70, 2)
        expected_total = round(200_000 + expected_extra, 2)
        assert total == expected_total
        assert breakdown["extra_days_cost"] == expected_extra

    def test_per_guest_pricing(self):
        vendor = make_vendor(base_price=0, price_per_guest=450.0)
        total, breakdown = _calculate_price(vendor, guest_count=500, duration_days=1)
        assert total == 225_000.0
        assert breakdown["per_guest_cost"] == 225_000.0

    def test_per_guest_multi_day(self):
        vendor = make_vendor(base_price=0, price_per_guest=450.0)
        total, breakdown = _calculate_price(vendor, guest_count=500, duration_days=2)
        base = 225_000.0
        extra = round(base * 0.70, 2)
        assert total == round(base + extra, 2)

    def test_zero_guests_per_guest_pricing(self):
        vendor = make_vendor(base_price=0, price_per_guest=450.0)
        total, breakdown = _calculate_price(vendor, guest_count=None, duration_days=1)
        # No guests provided — should return 0 or handle gracefully
        assert total == 0.0

    def test_price_is_deterministic(self):
        vendor = make_vendor(base_price=150_000)
        results = [_calculate_price(vendor, None, 1)[0] for _ in range(10)]
        assert all(r == results[0] for r in results)


# ── Negotiation tests ─────────────────────────────────────────────────────────

class TestNegotiateRules:
    def test_offer_at_quoted_price_accepted(self):
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        result = _negotiate_rules(vendor, offer_price=200_000, round_number=1)
        assert result.vendor_response == "accepted"
        assert result.final_price == 200_000

    def test_offer_above_quoted_accepted(self):
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        result = _negotiate_rules(vendor, offer_price=210_000, round_number=1)
        assert result.vendor_response == "accepted"

    def test_above_floor_round1_counter(self):
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        result = _negotiate_rules(vendor, offer_price=170_000, round_number=1)
        assert result.vendor_response == "counter"
        assert result.counter_price is not None
        # Counter should be between offer and quoted
        assert 170_000 < result.counter_price < 200_000

    def test_above_floor_round2_accepted(self):
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        result = _negotiate_rules(vendor, offer_price=170_000, round_number=2)
        assert result.vendor_response == "accepted"
        assert result.final_price == 170_000

    def test_below_floor_rejected(self):
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        result = _negotiate_rules(vendor, offer_price=140_000, round_number=1)
        assert result.vendor_response == "rejected"
        assert result.final_price is None

    def test_exactly_at_floor_round1_counter(self):
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        result = _negotiate_rules(vendor, offer_price=160_000, round_number=1)
        assert result.vendor_response == "counter"

    def test_counter_price_is_midpoint(self):
        """Counter price should be approximately the midpoint."""
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        result = _negotiate_rules(vendor, offer_price=170_000, round_number=1)
        expected_midpoint = round((170_000 + 200_000) / 2, -2)
        assert result.counter_price == expected_midpoint

    def test_negotiation_is_deterministic(self):
        vendor = make_vendor(base_price=200_000, price_floor=160_000)
        results = [
            _negotiate_rules(vendor, offer_price=170_000, round_number=1).vendor_response
            for _ in range(5)
        ]
        assert all(r == results[0] for r in results)
