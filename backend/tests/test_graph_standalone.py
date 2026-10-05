"""
Standalone tests for graph state, routing logic, and deterministic agent functions.
No database, no LLM, no API calls required.
"""

import sys, os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("SYNC_DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
os.environ.setdefault("GEMINI_API_KEY", "test-key")


# ── State tests ───────────────────────────────────────────────────────────────

def test_initial_state_defaults():
    from app.graph.state import initial_state
    s = initial_state(session_id="sess-001", rag_mode="agentic", llm_provider="gemini")
    assert s["session_id"] == "sess-001"
    assert s["rag_mode"] == "agentic"
    assert s["status"] == "created"
    assert s["requirements_complete"] is False
    assert s["critic_iterations"] == 0
    assert s["awaiting_human"] is False
    assert s["evidence"] == []
    assert s["vendor_selections"] == []


def test_initial_state_different_modes():
    from app.graph.state import initial_state
    s = initial_state("s2", rag_mode="none", llm_provider="groq")
    assert s["rag_mode"] == "none"
    assert s["llm_provider"] == "groq"


# ── Intake Agent helpers ──────────────────────────────────────────────────────

def test_normalise_requirements_event_type():
    from app.graph.nodes.intake import _normalise_requirements
    req = {"event_type": "WEDDING", "guest_count": "500", "budget": "1500000"}
    result = _normalise_requirements(req)
    assert result["event_type"] == "wedding"
    assert result["guest_count"] == 500
    assert result["budget"] == 1_500_000.0


def test_normalise_requirements_invalid_event():
    from app.graph.nodes.intake import _normalise_requirements
    req = {"event_type": "concert"}
    result = _normalise_requirements(req)
    assert "event_type" not in result


def test_normalise_duration_default():
    from app.graph.nodes.intake import _normalise_requirements
    req = {"event_type": "wedding"}
    result = _normalise_requirements(req)
    assert result["duration_days"] == 1


def test_merge_requirements_basic():
    from app.graph.nodes.intake import _merge_requirements
    existing = {"event_type": "wedding", "city": "Chennai"}
    extracted = {"guest_count": 500, "budget": 1_500_000}
    merged = _merge_requirements(existing, extracted, is_update=False)
    assert merged["event_type"] == "wedding"
    assert merged["city"] == "Chennai"
    assert merged["guest_count"] == 500


def test_merge_requirements_update_budget():
    from app.graph.nodes.intake import _merge_requirements
    existing = {"budget": 1_500_000, "city": "Chennai"}
    extracted = {"budget": 1_800_000}
    merged = _merge_requirements(existing, extracted, is_update=True)
    assert merged["budget"] == 1_800_000


def test_ask_for_missing_single():
    from app.graph.nodes.intake import _ask_for_missing
    msg = _ask_for_missing(["date"], {})
    assert "date" in msg.lower()


def test_ask_for_missing_multiple():
    from app.graph.nodes.intake import _ask_for_missing
    msg = _ask_for_missing(["city", "budget"], {})
    assert "city" in msg.lower() or "city" in msg
    assert "budget" in msg.lower()


# ── Routing logic tests ───────────────────────────────────────────────────────

def test_intake_router_complete():
    from app.graph.graph import intake_router
    from app.graph.state import initial_state
    from langgraph.graph import END
    s = initial_state("s1")
    s["requirements_complete"] = True
    assert intake_router(s) == "feasibility"


def test_intake_router_incomplete():
    from app.graph.graph import intake_router
    from app.graph.state import initial_state
    from langgraph.graph import END
    s = initial_state("s1")
    s["requirements_complete"] = False
    assert intake_router(s) == END


def test_feasibility_router_feasible():
    from app.graph.graph import feasibility_router
    from app.graph.state import initial_state
    s = initial_state("s1")
    s["feasibility"] = {"feasible": True}
    assert feasibility_router(s) == "planner"


def test_feasibility_router_infeasible():
    from app.graph.graph import feasibility_router
    from app.graph.state import initial_state

    s = initial_state("s1")
    s["feasibility"] = {"feasible": False}

    # Initial feasibility is a screening step.
    # Research should investigate missing evidence before final infeasibility.
    assert feasibility_router(s) == "planner"


def test_critic_router_passed():
    from app.graph.graph import critic_router
    from app.graph.state import initial_state
    s = initial_state("s1")
    s["critic_feedback"] = [{"passed": True, "issues": [], "iteration": 1}]
    s["critic_iterations"] = 1
    assert critic_router(s) == "human_review"


def test_critic_router_failed_first_iteration():
    from app.graph.graph import critic_router
    from app.graph.state import initial_state
    s = initial_state("s1")
    s["critic_feedback"] = [{"passed": False, "issues": [{"severity": "high"}], "iteration": 1}]
    s["critic_iterations"] = 1
    assert critic_router(s) == "planner"


def test_critic_router_failed_max_iterations():
    from app.graph.graph import critic_router
    from app.graph.state import initial_state
    s = initial_state("s1")
    s["critic_feedback"] = [{"passed": False, "issues": [], "iteration": 2}]
    s["critic_iterations"] = 2  # at max
    assert critic_router(s) == "human_review"


def test_human_router_approve():
    from app.graph.graph import human_router
    from app.graph.state import initial_state
    s = initial_state("s1")
    s["status"] = "booking"
    assert human_router(s) == "booking"


def test_human_router_modify():
    from app.graph.graph import human_router
    from app.graph.state import initial_state
    s = initial_state("s1")
    s["status"] = "replanning"
    assert human_router(s) == "planner"


# ── Critic checks ─────────────────────────────────────────────────────────────

def test_critic_detects_missing_mandatory():
    """Critic should flag missing mandatory category."""
    import asyncio

    async def _run():
        from app.graph.nodes.critic import critic_node
        from app.graph.state import initial_state
        s = initial_state("sess-critic")
        s["requirements"] = {
            "event_type": "wedding",
            "guest_count": 500,
            "budget": 1_500_000,
            "date": "2026-12-20",
        }
        # No venue selection — critic should flag it
        s["vendor_selections"] = [
            {"vendor_id": "V1", "category": "catering", "name": "Test Catering",
             "quoted_price": 200000, "evidence_ids": ["EV-001"], "critic_warnings": []},
        ]
        s["budget_summary"] = {"spent": 200000, "over_budget": False}
        s["evidence"] = [{"evidence_id": "EV-001", "score": 0.8}]
        s["critic_iterations"] = 0

        result = await critic_node(s, {"configurable": {"db": None}})
        feedback = result["critic_feedback"][-1]
        issue_types = [i["type"] for i in feedback["issues"]]
        assert "missing_mandatory_category" in issue_types
        assert feedback["passed"] is False

    asyncio.run(_run())


def test_critic_detects_missing_evidence():
    """Critic should flag vendor with no evidence IDs."""
    import asyncio

    async def _run():
        from app.graph.nodes.critic import critic_node
        from app.graph.state import initial_state
        s = initial_state("sess-ev")
        s["requirements"] = {
            "event_type": "birthday",
            "guest_count": 50,
            "budget": 80_000,
        }
        s["vendor_selections"] = [
            {"vendor_id": "V1", "category": "venue", "name": "Party Hall",
             "quoted_price": 15000, "evidence_ids": [], "critic_warnings": []},
            {"vendor_id": "V2", "category": "catering", "name": "Snacks",
             "quoted_price": 20000, "evidence_ids": [], "critic_warnings": []},
            {"vendor_id": "V3", "category": "decoration", "name": "Decor",
             "quoted_price": 10000, "evidence_ids": [], "critic_warnings": []},
        ]
        s["budget_summary"] = {"spent": 45000, "over_budget": False}
        s["evidence"] = []
        s["critic_iterations"] = 0

        result = await critic_node(s, {"configurable": {"db": None}})
        feedback = result["critic_feedback"][-1]
        issue_types = [i["type"] for i in feedback["issues"]]
        assert "missing_evidence" in issue_types

    asyncio.run(_run())


def test_critic_passes_valid_plan():
    """A complete, grounded, within-budget plan should pass."""
    import asyncio

    async def _run():
        from app.graph.nodes.critic import critic_node
        from app.graph.state import initial_state
        s = initial_state("sess-pass")
        s["requirements"] = {
            "event_type": "birthday",
            "guest_count": 50,
            "budget": 80_000,
        }
        s["vendor_selections"] = [
            {"vendor_id": "V1", "category": "venue", "name": "Party Hall",
             "quoted_price": 15000, "evidence_ids": ["EV-001"], "critic_warnings": []},
            {"vendor_id": "V2", "category": "catering", "name": "Snacks",
             "quoted_price": 20000, "evidence_ids": ["EV-002"], "critic_warnings": []},
            {"vendor_id": "V3", "category": "decoration", "name": "Decor",
             "quoted_price": 8000, "evidence_ids": ["EV-003"], "critic_warnings": []},
        ]
        s["budget_summary"] = {"spent": 43000, "over_budget": False}
        s["evidence"] = [
            {"evidence_id": "EV-001", "score": 0.9},
            {"evidence_id": "EV-002", "score": 0.85},
            {"evidence_id": "EV-003", "score": 0.8},
        ]
        s["critic_iterations"] = 0

        result = await critic_node(s, {"configurable": {"db": None}})
        feedback = result["critic_feedback"][-1]
        high_issues = [i for i in feedback["issues"] if i.get("severity") == "high"]
        assert len(high_issues) == 0
        assert feedback["passed"] is True

    asyncio.run(_run())


# ── Budget Agent tests ────────────────────────────────────────────────────────

def test_budget_node_calculates_correctly():
    import asyncio

    async def _run():
        from app.graph.nodes.budget import budget_node
        from app.graph.state import initial_state
        s = initial_state("sess-budget")
        s["requirements"] = {"budget": 1_500_000, "event_type": "wedding"}
        s["vendor_selections"] = [
            {"vendor_id": "V1", "category": "venue", "name": "Hall",
             "quoted_price": 350_000, "final_price": None, "negotiation_savings": 0,
             "critic_warnings": []},
            {"vendor_id": "V2", "category": "catering", "name": "Caterer",
             "quoted_price": 450_000, "final_price": None, "negotiation_savings": 0,
             "critic_warnings": []},
        ]
        s["budget_breakdown"] = {"venue": 420_000, "catering": 525_000}

        result = await budget_node(s, {"configurable": {"db": None}})
        assert result["category_actuals"]["venue"] == 350_000
        assert result["category_actuals"]["catering"] == 450_000
        assert result["budget_summary"]["spent"] == 800_000
        assert result["budget_summary"]["remaining"] == 700_000
        assert result["budget_summary"]["over_budget"] is False

    asyncio.run(_run())


def test_budget_node_detects_over_budget():
    import asyncio

    async def _run():
        from app.graph.nodes.budget import budget_node
        from app.graph.state import initial_state
        s = initial_state("sess-overbudget")
        s["requirements"] = {"budget": 500_000, "event_type": "wedding"}
        s["vendor_selections"] = [
            {"vendor_id": "V1", "category": "venue", "name": "Hall",
             "quoted_price": 400_000, "final_price": None, "negotiation_savings": 0,
             "critic_warnings": []},
            {"vendor_id": "V2", "category": "catering", "name": "Caterer",
             "quoted_price": 300_000, "final_price": None, "negotiation_savings": 0,
             "critic_warnings": []},
        ]
        s["budget_breakdown"] = {"venue": 140_000, "catering": 175_000}

        result = await budget_node(s, {"configurable": {"db": None}})
        assert result["budget_summary"]["over_budget"] is True
        assert result["budget_summary"]["remaining"] < 0

    asyncio.run(_run())


# ── Planner deterministic fallback ────────────────────────────────────────────

def test_planner_deterministic_needs():
    from app.graph.nodes.planner import _deterministic_information_needs
    needs = _deterministic_information_needs(
        categories=["venue", "catering", "decoration"],
        req={"event_type": "wedding", "city": "Chennai", "guest_count": 500, "date": "2026-12-20"},
        budget_breakdown={"venue": 420_000, "catering": 525_000, "decoration": 180_000},
        mandatory=["venue", "catering", "decoration"],
    )
    assert len(needs) == 3
    cats = {n["category"] for n in needs}
    assert "venue" in cats
    assert "catering" in cats
    all_mandatory = all(n["priority"] == "mandatory" for n in needs)
    assert all_mandatory


def test_planner_deterministic_capacity_in_constraints():
    from app.graph.nodes.planner import _deterministic_information_needs
    needs = _deterministic_information_needs(
        categories=["venue"],
        req={"event_type": "wedding", "city": "Chennai", "guest_count": 500},
        budget_breakdown={"venue": 420_000},
        mandatory=["venue"],
    )
    assert needs[0]["constraints"].get("min_capacity") == 500


# ── Graph build test ──────────────────────────────────────────────────────────

def test_graph_builds_successfully():
    from app.graph.graph import build_graph
    graph = build_graph()
    assert graph is not None
    # Check all expected nodes exist
    nodes = set(graph.nodes.keys()) if hasattr(graph, 'nodes') else set()
    # Just verify it compiled without error
    assert graph is not None


if __name__ == "__main__":
    tests = [
        test_initial_state_defaults,
        test_initial_state_different_modes,
        test_normalise_requirements_event_type,
        test_normalise_requirements_invalid_event,
        test_normalise_duration_default,
        test_merge_requirements_basic,
        test_merge_requirements_update_budget,
        test_ask_for_missing_single,
        test_ask_for_missing_multiple,
        test_intake_router_complete,
        test_intake_router_incomplete,
        test_feasibility_router_feasible,
        test_feasibility_router_infeasible,
        test_critic_router_passed,
        test_critic_router_failed_first_iteration,
        test_critic_router_failed_max_iterations,
        test_human_router_approve,
        test_human_router_modify,
        test_critic_detects_missing_mandatory,
        test_critic_detects_missing_evidence,
        test_critic_passes_valid_plan,
        test_budget_node_calculates_correctly,
        test_budget_node_detects_over_budget,
        test_planner_deterministic_needs,
        test_planner_deterministic_capacity_in_constraints,
        test_graph_builds_successfully,
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
