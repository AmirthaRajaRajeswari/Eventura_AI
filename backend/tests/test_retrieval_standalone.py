"""
Standalone unit tests for the retrieval layer.
No database required — tests deterministic helpers only.
"""

import sys, os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("SYNC_DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
os.environ.setdefault("GEMINI_API_KEY", "test-key")


# ── Evidence tests ────────────────────────────────────────────────────────────

def test_evidence_registry_sequential():
    from app.retrieval.evidence import EvidenceRegistry
    reg = EvidenceRegistry()
    assert reg.next_id("s1") == "EV-001"
    assert reg.next_id("s1") == "EV-002"
    assert reg.next_id("s1") == "EV-003"


def test_evidence_registry_per_session():
    from app.retrieval.evidence import EvidenceRegistry
    reg = EvidenceRegistry()
    assert reg.next_id("s1") == "EV-001"
    assert reg.next_id("s2") == "EV-001"  # independent counter
    assert reg.next_id("s1") == "EV-002"


def test_evidence_reset():
    from app.retrieval.evidence import EvidenceRegistry
    reg = EvidenceRegistry()
    reg.next_id("s1")
    reg.next_id("s1")
    reg.reset("s1")
    assert reg.next_id("s1") == "EV-001"


def test_make_evidence():
    from app.retrieval.evidence import make_evidence, evidence_registry
    evidence_registry.reset("test_make")
    ev = make_evidence(
        session_id="test_make",
        source_type="vendor_sql",
        source_ref="VEN-001",
        content="Test vendor",
        score=0.85,
        query="venue Chennai",
        retrieval_round=0,
    )
    assert ev.evidence_id == "EV-001"
    assert ev.score == 0.85
    d = ev.to_dict()
    assert d["evidence_id"] == "EV-001"
    assert d["source_type"] == "vendor_sql"


# ── Feasibility tests ─────────────────────────────────────────────────────────

def test_budget_breakdown_wedding():
    from app.retrieval.feasibility import calculate_budget_breakdown
    bd = calculate_budget_breakdown(1_500_000, "wedding", 500, 2)
    assert "venue" in bd
    assert "catering" in bd
    # Ratios should sum close to 1
    total = sum(bd.values())
    assert abs(total - 1_500_000) < 50_000  # rounding tolerance


def test_budget_breakdown_birthday():
    from app.retrieval.feasibility import calculate_budget_breakdown
    bd = calculate_budget_breakdown(80_000, "birthday", 50, 1)
    assert "venue" in bd
    assert "cake" in bd
    assert all(v >= 0 for v in bd.values())


def test_calculate_remaining_budget():
    from app.retrieval.feasibility import calculate_remaining_budget
    result = calculate_remaining_budget(
        total_budget=1_500_000,
        category_costs={"venue": 420_000, "catering": 525_000},
    )
    assert result["spent"] == 945_000
    assert result["remaining"] == 555_000
    assert result["over_budget"] is False


def test_over_budget_detection():
    from app.retrieval.feasibility import calculate_remaining_budget
    result = calculate_remaining_budget(
        total_budget=500_000,
        category_costs={"venue": 400_000, "catering": 300_000},
    )
    assert result["over_budget"] is True
    assert result["remaining"] == -200_000


def test_apply_budget_reduction():
    from app.retrieval.feasibility import apply_budget_reduction
    new_budget, new_alloc = apply_budget_reduction(
        current_budget=1_500_000,
        reduction_pct=15.0,
        category_allocations={"venue": 420_000, "catering": 525_000},
    )
    assert new_budget == 1_275_000.0
    assert new_alloc["venue"] == round(420_000 * 0.85, 2)
    assert new_alloc["catering"] == round(525_000 * 0.85, 2)


def test_budget_reduction_deterministic():
    from app.retrieval.feasibility import apply_budget_reduction
    results = [
        apply_budget_reduction(1_000_000, 15.0, {"venue": 300_000})[0]
        for _ in range(5)
    ]
    assert all(r == 850_000.0 for r in results)


# ── RAG mode routing tests ────────────────────────────────────────────────────

def test_needs_vendor_data_categories():
    from app.retrieval.rag_modes import _needs_vendor_data
    assert _needs_vendor_data("venue") is True
    assert _needs_vendor_data("catering") is True
    assert _needs_vendor_data("photography") is True
    assert _needs_vendor_data("weather") is False


def test_derive_max_price():
    from app.retrieval.rag_modes import _derive_max_price
    price = _derive_max_price(
        category="venue",
        requirements={"budget": 1_500_000},
        constraints={},
    )
    # 32% * 1.3 buffer = 41.6% of budget
    expected = round(1_500_000 * 0.32 * 1.30, -3)
    assert price == expected


def test_derive_max_price_no_budget():
    from app.retrieval.rag_modes import _derive_max_price
    price = _derive_max_price(
        category="venue",
        requirements={},
        constraints={"max_price": 500_000},
    )
    assert price == 500_000


def test_check_sufficiency_no_vendors():
    from app.retrieval.rag_modes import _check_sufficiency
    sufficient, notes = _check_sufficiency(
        category="venue",
        vendors=[],
        knowledge=[],
        requirements={"city": "Chennai"},
        constraints={},
        retrieval_round=0,
    )
    assert sufficient is False
    assert "venue" in notes.lower()


def test_check_sufficiency_with_vendors():
    from unittest.mock import MagicMock
    from app.retrieval.rag_modes import _check_sufficiency

    v = MagicMock()
    v.vendor_id = "VEN-001"
    v.is_available = True
    v.max_capacity = 600

    sufficient, notes = _check_sufficiency(
        category="venue",
        vendors=[v],
        knowledge=[],
        requirements={"city": "Chennai", "guest_count": 500, "date": "2026-12-20"},
        constraints={},
        retrieval_round=0,
    )
    assert sufficient is True


def test_refine_query_capacity_issue():
    from app.retrieval.rag_modes import _refine_query
    q = _refine_query(
        category="venue",
        event_type="wedding",
        city="Chennai",
        constraints={},
        insufficiency_reason="No venue found with capacity >= 500 guests",
        previous_vendors=[],
    )
    assert "capacity" in q.lower() or "large" in q.lower()


def test_build_information_need():
    from app.retrieval.interface import build_information_need
    need = build_information_need(
        category="venue",
        event_type="wedding",
        city="Chennai",
        constraints={"min_capacity": 500},
    )
    assert need["category"] == "venue"
    assert need["constraints"]["min_capacity"] == 500
    assert "wedding" in need["description"].lower()


# ── Cosine similarity test ────────────────────────────────────────────────────

def test_cosine_similarity_identical():
    from app.retrieval.embeddings import cosine_similarity
    v = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    from app.retrieval.embeddings import cosine_similarity
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_cosine_similarity_zero_vector():
    from app.retrieval.embeddings import cosine_similarity
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


if __name__ == "__main__":
    tests = [
        test_evidence_registry_sequential,
        test_evidence_registry_per_session,
        test_evidence_reset,
        test_make_evidence,
        test_budget_breakdown_wedding,
        test_budget_breakdown_birthday,
        test_calculate_remaining_budget,
        test_over_budget_detection,
        test_apply_budget_reduction,
        test_budget_reduction_deterministic,
        test_needs_vendor_data_categories,
        test_derive_max_price,
        test_derive_max_price_no_budget,
        test_check_sufficiency_no_vendors,
        test_check_sufficiency_with_vendors,
        test_refine_query_capacity_issue,
        test_build_information_need,
        test_cosine_similarity_identical,
        test_cosine_similarity_orthogonal,
        test_cosine_similarity_zero_vector,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            import traceback
            print(f"  FAIL  {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} tests passed")
