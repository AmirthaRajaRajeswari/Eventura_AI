"""
Evaluation API for Eventura AI.

Endpoints:
  POST /api/v1/eval/run     — start an evaluation run
  GET  /api/v1/eval/results — get evaluation results
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EvalResultsOut, EvalRunRequest, EvalRunResponse
from app.db.models import EvalRun
from app.db.session import get_db
from app.logger import get_logger

router = APIRouter(prefix="/api/v1/eval", tags=["evaluation"])
logger = get_logger(__name__)


@router.post("/run", response_model=EvalRunResponse)
async def start_eval_run(
    req: EvalRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> EvalRunResponse:
    """
    Start an evaluation run. Runs in background.
    See eval/ directory for the full evaluation framework.
    """
    run_id = str(uuid.uuid4())[:12]
    total = (
        len(req.scenario_ids or ["all"])
        * len(req.rag_modes)
        * len(req.llm_providers)
        * len(req.critic_enabled_values)
        * req.runs_per_scenario
    )

    # Estimated ~30s per scenario run
    estimated_minutes = round(total * 0.5, 1)

    background_tasks.add_task(
        _run_evaluation_background,
        run_id=run_id,
        req=req,
    )

    logger.info("Evaluation run started", run_id=run_id, total_runs=total)

    return EvalRunResponse(
        run_id=run_id,
        scenarios_queued=total,
        estimated_duration_minutes=estimated_minutes,
        status="started",
    )


@router.get("/results", response_model=EvalResultsOut)
async def get_eval_results(
    db: AsyncSession = Depends(get_db),
) -> EvalResultsOut:
    """Get all evaluation results."""
    result = await db.execute(
        select(EvalRun).order_by(EvalRun.created_at.desc()).limit(500)
    )
    runs = result.scalars().all()

    run_dicts = []
    for r in runs:
        run_dicts.append({
            "id": r.id,
            "scenario_id": r.scenario_id,
            "rag_mode": r.rag_mode,
            "llm_provider": r.llm_provider,
            "critic_enabled": r.critic_enabled,
            "run_index": r.run_index,
            "constraint_satisfaction": r.constraint_satisfaction,
            "budget_adherence": r.budget_adherence,
            "evidence_grounding": r.evidence_grounding,
            "hallucination_rate": r.hallucination_rate,
            "task_completion": r.task_completion,
            "infeasibility_detected": r.infeasibility_detected,
            "latency_ms": r.latency_ms,
            "total_tokens": r.total_tokens,
            "estimated_cost_usd": r.estimated_cost_usd,
            "error": r.error,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })

    # Build summary
    summary = _build_summary(run_dicts)

    return EvalResultsOut(
        runs=run_dicts,
        summary=summary,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _build_summary(runs: list[dict]) -> dict:
    if not runs:
        return {"total_runs": 0, "by_rag_mode": {}, "by_llm": {}}

    def avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    # Group by rag_mode
    by_rag: dict = {}
    by_llm: dict = {}

    for r in runs:
        mode = r["rag_mode"]
        llm = r["llm_provider"]

        if mode not in by_rag:
            by_rag[mode] = []
        by_rag[mode].append(r)

        if llm not in by_llm:
            by_llm[llm] = []
        by_llm[llm].append(r)

    def summarise_group(group):
        return {
            "count": len(group),
            "constraint_satisfaction": avg([r["constraint_satisfaction"] for r in group]),
            "budget_adherence": avg([r["budget_adherence"] for r in group]),
            "evidence_grounding": avg([r["evidence_grounding"] for r in group]),
            "task_completion": avg([r["task_completion"] for r in group]),
            "avg_latency_ms": avg([r["latency_ms"] for r in group]),
        }

    return {
        "total_runs": len(runs),
        "by_rag_mode": {mode: summarise_group(grp) for mode, grp in by_rag.items()},
        "by_llm": {llm: summarise_group(grp) for llm, grp in by_llm.items()},
    }


async def _run_evaluation_background(run_id: str, req: EvalRunRequest) -> None:
    """Dispatch to the eval runner (Phase 8)."""
    try:
        from eval.run_eval import run_evaluation
        await run_evaluation(run_id=run_id, req=req)
    except ImportError:
        logger.warning("Eval runner not yet implemented — Phase 8")
    except Exception as e:
        logger.error("Evaluation failed", run_id=run_id, error=str(e))
