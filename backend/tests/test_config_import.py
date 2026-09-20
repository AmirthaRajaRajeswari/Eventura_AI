"""Verify core modules import without error (no DB required)."""
import sys, os

# Minimal env so pydantic-settings doesn't complain
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("SYNC_DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
os.environ.setdefault("GEMINI_API_KEY", "test-key")


def test_config_imports():
    from app.config import settings
    assert settings.llm_provider == "gemini"


def test_llm_info():
    # Only test the info helper — do NOT call get_llm() which imports provider SDKs
    from app.config import settings
    assert settings.llm_provider in ("gemini", "groq", "ollama")
    assert settings.gemini_model  # non-empty


def test_mock_vendor_schemas():
    from app.mock_vendors.schemas import VendorOut, QuoteRequest, NegotiateRequest
    q = QuoteRequest(date="2026-12-20", guest_count=500, duration_days=2)
    assert q.guest_count == 500


def test_vendor_synthetic_disclaimer():
    from app.mock_vendors.schemas import VendorListOut
    out = VendorListOut(vendors=[], total=0)
    assert "synthetic" in out.synthetic_disclaimer.lower()


if __name__ == "__main__":
    tests = [test_config_imports, test_llm_info, test_mock_vendor_schemas, test_vendor_synthetic_disclaimer]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
