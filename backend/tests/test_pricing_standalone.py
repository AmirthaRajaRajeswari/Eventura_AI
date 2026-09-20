"""
Standalone unit tests for deterministic pricing and negotiation logic.
Runs without any database or FastAPI dependencies.
"""

from unittest.mock import MagicMock


def make_vendor(base_price=200_000.0, price_per_guest=None, price_floor=160_000.0):
    v = MagicMock()
    v.id = "VEN-TEST"
    v.base_price = base_price
    v.price_per_guest = price_per_guest
    v.price_floor = price_floor
    return v


# ── Copied deterministic functions (self-contained for this test) ─────────────

def calculate_price(vendor, guest_count, duration_days):
    breakdown = {}
    if vendor.price_per_guest and guest_count:
        cost = round(vendor.price_per_guest * guest_count, 2)
        breakdown["per_guest_cost"] = cost
        base = cost
    else:
        base = vendor.base_price
        breakdown["base_price"] = base

    if duration_days > 1:
        extra = round(base * 0.70 * (duration_days - 1), 2)
        breakdown["extra_days_cost"] = extra
        total = round(base + extra, 2)
    else:
        total = round(base, 2)

    breakdown["total"] = total
    return total, breakdown


def negotiate(vendor, offer_price, round_number):
    quoted = vendor.base_price if vendor.base_price > 0 else 50_000.0
    floor = vendor.price_floor

    if offer_price >= quoted:
        return "accepted", offer_price, None
    elif offer_price >= floor and round_number == 1:
        counter = round((offer_price + quoted) / 2, -2)
        return "counter", None, counter
    elif offer_price >= floor and round_number >= 2:
        return "accepted", offer_price, None
    else:
        return "rejected", None, None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_base_price_single_day():
    v = make_vendor(base_price=200_000)
    total, bd = calculate_price(v, None, 1)
    assert total == 200_000.0
    assert bd["base_price"] == 200_000.0


def test_base_price_two_days():
    v = make_vendor(base_price=200_000)
    total, bd = calculate_price(v, None, 2)
    assert bd["extra_days_cost"] == 140_000.0
    assert total == 340_000.0


def test_per_guest_pricing():
    v = make_vendor(base_price=0, price_per_guest=450.0)
    total, bd = calculate_price(v, 500, 1)
    assert total == 225_000.0


def test_per_guest_two_days():
    v = make_vendor(base_price=0, price_per_guest=450.0)
    total, _ = calculate_price(v, 500, 2)
    assert total == 225_000.0 + round(225_000.0 * 0.70, 2)


def test_deterministic_repeated():
    v = make_vendor(base_price=150_000)
    results = [calculate_price(v, None, 1)[0] for _ in range(10)]
    assert all(r == 150_000.0 for r in results)


def test_negotiate_at_quoted_accepted():
    v = make_vendor(base_price=200_000, price_floor=160_000)
    status, final, counter = negotiate(v, 200_000, 1)
    assert status == "accepted"
    assert final == 200_000


def test_negotiate_above_quoted_accepted():
    v = make_vendor(base_price=200_000, price_floor=160_000)
    status, final, _ = negotiate(v, 210_000, 1)
    assert status == "accepted"


def test_negotiate_above_floor_round1_counter():
    v = make_vendor(base_price=200_000, price_floor=160_000)
    status, _, counter = negotiate(v, 170_000, 1)
    assert status == "counter"
    assert counter is not None
    assert 170_000 < counter < 200_000
    # midpoint check
    assert counter == round((170_000 + 200_000) / 2, -2)


def test_negotiate_above_floor_round2_accepted():
    v = make_vendor(base_price=200_000, price_floor=160_000)
    status, final, _ = negotiate(v, 170_000, 2)
    assert status == "accepted"
    assert final == 170_000


def test_negotiate_below_floor_rejected():
    v = make_vendor(base_price=200_000, price_floor=160_000)
    status, final, counter = negotiate(v, 140_000, 1)
    assert status == "rejected"
    assert final is None
    assert counter is None


def test_negotiate_deterministic():
    v = make_vendor(base_price=200_000, price_floor=160_000)
    results = [negotiate(v, 170_000, 1)[0] for _ in range(5)]
    assert all(r == "counter" for r in results)


if __name__ == "__main__":
    tests = [
        test_base_price_single_day,
        test_base_price_two_days,
        test_per_guest_pricing,
        test_per_guest_two_days,
        test_deterministic_repeated,
        test_negotiate_at_quoted_accepted,
        test_negotiate_above_quoted_accepted,
        test_negotiate_above_floor_round1_counter,
        test_negotiate_above_floor_round2_accepted,
        test_negotiate_below_floor_rejected,
        test_negotiate_deterministic,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
