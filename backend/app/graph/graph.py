"""
Main LangGraph event planning graph for Eventura AI.

Graph topology:

    intake → feasibility → planner → research → budget → negotiator
                                      ↓
                                    critic
                                      ↓
                           ┌──────────┴──────────┐
                           │                     │
                      re-plan                  HITL
                           │                     │
                           └──── planner     ┌───┴────┐
                                             │        │
                                        modify/     approve
                                        reject        │
                                             │        ↓
                                        feasibility booking → END

HITL is implemented with LangGraph interrupt() inside human_review_node.

Conditional routing:
  - intake_router:
        complete → feasibility
        needs_info → END

  - critic_router:
        passed → human_review
        failed + iterations < 2 → planner
        failed + iterations >= 2 → human_review

  - human_router:
        approve → booking
        modify/reject → feasibility
        researching → planner
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


# ─────────────────────────────────────────────────────────────────────────────
# Conditional routing functions
# ─────────────────────────────────────────────────────────────────────────────

def intake_router(state: EventState) -> str:
    """
    Route after intake.

    If all critical requirements are available, continue to feasibility.
    Otherwise stop and wait for the user to provide missing information.
    """
    if state.get("requirements_complete"):
        return "feasibility"

    return END


def critic_router(state: EventState) -> str:
    """
    Route after critic evaluation.

    Passed:
        → human_review

    Failed with fewer than 2 iterations:
        → planner for another correction cycle

    Failed after maximum iterations:
        → human_review with warnings
    """
    feedback_list = state.get("critic_feedback", [])

    if not feedback_list:
        return "human_review"

    last_feedback = feedback_list[-1]

    passed = last_feedback.get("passed", False)
    iterations = state.get("critic_iterations", 0)

    if passed:
        return "human_review"

    if iterations < 2:
        return "planner"

    # Maximum autonomous critic iterations reached.
    # Human gets the final decision.
    return "human_review"


def human_router(state: EventState) -> str:
    """
    Route after human review.

    approve:
        → booking

    modify/reject:
        → feasibility

    researching:
        → planner

    The feasibility step is intentionally repeated after a human
    modification/rejection because the requirements or vendor constraints
    may have changed. This prevents stale feasibility information from
    being reused.
    """
    status = state.get("status", "")

    if status == "booking":
        return "booking"

    if status == "replanning":
        return "feasibility"

    if status == "researching":
        return "planner"

    # Default behavior is approval/booking.
    return "booking"


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────

def build_graph(checkpointer=None) -> StateGraph:
    """
    Build and compile the Eventura AI planning graph.

    Parameters
    ----------
    checkpointer:
        LangGraph checkpointer used for state persistence.

        Defaults to MemorySaver for development/testing.

        A PostgreSQL-backed checkpointer can be supplied later for
        persistent production deployments.
    """

    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(EventState)

    # ─────────────────────────────────────────────────────────────────────
    # Nodes
    # ─────────────────────────────────────────────────────────────────────

    graph.add_node("intake", intake_node)
    graph.add_node("feasibility", feasibility_node)
    graph.add_node("planner", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("budget", budget_node)
    graph.add_node("negotiator", negotiator_node)
    graph.add_node("critic", critic_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("booking", booking_node)

    # ─────────────────────────────────────────────────────────────────────
    # Entry point
    # ─────────────────────────────────────────────────────────────────────

    graph.set_entry_point("intake")

    # ─────────────────────────────────────────────────────────────────────
    # Intake → Feasibility or END
    # ─────────────────────────────────────────────────────────────────────

    graph.add_conditional_edges(
        "intake",
        intake_router,
        {
            "feasibility": "feasibility",
            END: END,
        },
    )

    # ─────────────────────────────────────────────────────────────────────
    # Feasibility → Planner
    # ─────────────────────────────────────────────────────────────────────

    graph.add_edge("feasibility", "planner")

    # ─────────────────────────────────────────────────────────────────────
    # Planner → Research
    # ─────────────────────────────────────────────────────────────────────

    graph.add_edge("planner", "research")

    # ─────────────────────────────────────────────────────────────────────
    # Research → Budget
    # ─────────────────────────────────────────────────────────────────────

    graph.add_edge("research", "budget")

    # ─────────────────────────────────────────────────────────────────────
    # Budget → Negotiator
    # ─────────────────────────────────────────────────────────────────────

    graph.add_edge("budget", "negotiator")

    # ─────────────────────────────────────────────────────────────────────
    # Negotiator → Critic
    # ─────────────────────────────────────────────────────────────────────

    graph.add_edge("negotiator", "critic")

    # ─────────────────────────────────────────────────────────────────────
    # Critic → Planner or Human Review
    # ─────────────────────────────────────────────────────────────────────

    graph.add_conditional_edges(
        "critic",
        critic_router,
        {
            "human_review": "human_review",
            "planner": "planner",
        },
    )

    # ─────────────────────────────────────────────────────────────────────
    # Human Review → Booking / Feasibility / Planner
    #
    # IMPORTANT:
    # There must be ONLY ONE conditional-edge registration for
    # "human_review" using human_router.
    # ─────────────────────────────────────────────────────────────────────

    graph.add_conditional_edges(
        "human_review",
        human_router,
        {
            "booking": "booking",
            "feasibility": "feasibility",
            "planner": "planner",
        },
    )

    # ─────────────────────────────────────────────────────────────────────
    # Booking → END
    # ─────────────────────────────────────────────────────────────────────

    graph.add_edge("booking", END)

    return graph.compile(checkpointer=checkpointer)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level default graph
# ─────────────────────────────────────────────────────────────────────────────

_default_graph = None


def initialize_graph(checkpointer) -> None:
    """
    Initialize the application's shared graph with a persistent checkpointer.
    Called once during FastAPI startup.
    """
    global _default_graph

    _default_graph = build_graph(checkpointer=checkpointer)


def get_graph(checkpointer=None):
    """
    Get the compiled application graph.

    A custom checkpointer creates a new graph.
    Otherwise, return the shared application graph.
    """
    global _default_graph

    if checkpointer is not None:
        return build_graph(checkpointer=checkpointer)

    if _default_graph is None:
        # Development fallback.
        # Normally initialize_graph() is called during application startup.
        _default_graph = build_graph()

    return _default_graph