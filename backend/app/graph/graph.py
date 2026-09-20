"""
Main LangGraph event planning graph for Eventura AI.

Graph topology:
  intake → feasibility → planner → research → budget → negotiator
         → critic → [replanning loop] → human_review → booking → END

HITL is implemented with LangGraph interrupt() inside human_review_node.
The graph checkpoints state to PostgreSQL via AsyncSqliteSaver (dev) or
langgraph-checkpoint-postgres (prod).

Conditional edges:
  - feasibility_router: feasible → planner | infeasible → END
  - critic_router:      passed → human_review | failed + iterations < 2 → planner | else → human_review
  - human_router:       approve → booking | modify/reject → planner
  - intake_router:      complete → feasibility | needs_info → END (wait)
  - replan_router:      disruption replan uses partial planner
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.graph.nodes.booking import booking_node
from app.graph.nodes.budget import budget_node
from app.graph.nodes.critic import critic_node
from app.graph.nodes.feasibility import feasibility_node
from app.graph.nodes.human_review import human_review_node
from app.graph.nodes.intake import intake_node
from app.graph.nodes.negotiator import negotiator_node
from app.graph.nodes.planner import planner_node
from app.graph.nodes.research import research_node
from app.graph.state import EventState
from app.logger import get_logger

logger = get_logger(__name__)


# ── Conditional routing functions ─────────────────────────────────────────────

def intake_router(state: EventState) -> str:
    """Route after intake: proceed if requirements complete, else wait."""
    if state.get("requirements_complete"):
        return "feasibility"
    return END  # Wait for user to provide missing fields


def feasibility_router(state: EventState) -> str:
    """Route after feasibility check."""
    feasibility = state.get("feasibility", {})
    if feasibility.get("feasible", False):
        return "planner"
    return END  # Infeasible — stop and inform user


def critic_router(state: EventState) -> str:
    """Route after critic evaluation."""
    feedback_list = state.get("critic_feedback", [])
    if not feedback_list:
        return "human_review"

    last_feedback = feedback_list[-1]
    passed = last_feedback.get("passed", False)
    iterations = state.get("critic_iterations", 0)

    if passed:
        return "human_review"
    elif iterations < 2:
        # Re-route to planner for correction
        return "planner"
    else:
        # Max iterations — proceed anyway with warnings
        return "human_review"


def human_router(state: EventState) -> str:
    """Route after human review."""
    status = state.get("status", "")
    if status == "booking":
        return "booking"
    elif status in ("replanning", "researching"):
        return "planner"
    return "booking"  # default


def post_booking_router(state: EventState) -> str:
    """After booking, go to END (run-of-show and invitations are separate flows)."""
    return END


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph(checkpointer=None) -> StateGraph:
    """
    Build and compile the Eventura AI planning graph.

    Parameters
    ----------
    checkpointer:
        LangGraph checkpointer for state persistence.
        Defaults to MemorySaver (in-memory, for development).
        Pass AsyncPostgresSaver for production.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(EventState)

    # ── Add nodes ─────────────────────────────────────────────────────────
    graph.add_node("intake", intake_node)
    graph.add_node("feasibility", feasibility_node)
    graph.add_node("planner", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("budget", budget_node)
    graph.add_node("negotiator", negotiator_node)
    graph.add_node("critic", critic_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("booking", booking_node)

    # ── Entry point ───────────────────────────────────────────────────────
    graph.set_entry_point("intake")

    # ── Edges ─────────────────────────────────────────────────────────────
    # Intake → feasibility or wait
    graph.add_conditional_edges(
        "intake",
        intake_router,
        {"feasibility": "feasibility", END: END},
    )

    # Feasibility → planner or stop
    graph.add_conditional_edges(
        "feasibility",
        feasibility_router,
        {"planner": "planner", END: END},
    )

    # Planner → research (always)
    graph.add_edge("planner", "research")

    # Research → budget
    graph.add_edge("research", "budget")

    # Budget → negotiator
    graph.add_edge("budget", "negotiator")

    # Negotiator → critic
    graph.add_edge("negotiator", "critic")

    # Critic → human_review or re-plan
    graph.add_conditional_edges(
        "critic",
        critic_router,
        {
            "human_review": "human_review",
            "planner": "planner",
        },
    )

    # Human review → booking or re-plan
    graph.add_conditional_edges(
        "human_review",
        human_router,
        {
            "booking": "booking",
            "planner": "planner",
        },
    )

    # Booking → END
    graph.add_edge("booking", END)

    return graph.compile(checkpointer=checkpointer, interrupt_before=["human_review"])


# Module-level default graph (MemorySaver for dev/testing)
_default_graph = None


def get_graph(checkpointer=None):
    """Get the compiled graph, creating it if needed."""
    global _default_graph
    if checkpointer is not None:
        return build_graph(checkpointer=checkpointer)
    if _default_graph is None:
        _default_graph = build_graph()
    return _default_graph
