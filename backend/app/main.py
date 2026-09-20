"""
Eventura AI — Main FastAPI application (port 8000).

All agentic event planning endpoints live here.
The mock vendor marketplace runs separately on port 8001.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Eventura AI starting",
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        rag_mode="agentic",
    )
    from app.llm.observability import setup_observability
    setup_observability()
    yield
    logger.info("Eventura AI shutting down")


app = FastAPI(
    title="Eventura AI",
    description=(
        "Agentic AI Event Planning and Coordination Platform. "
        "All demo vendor data is synthetic."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from app.mock_vendors.router import router as mock_vendor_router
from app.api.sessions import router as sessions_router
from app.api.eval import router as eval_router

app.include_router(mock_vendor_router)
app.include_router(sessions_router)
app.include_router(eval_router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "eventura-ai-backend",
        "llm_provider": settings.llm_provider,
        "disclaimer": (
            "All demo vendor and pricing data is synthetic and used "
            "for demonstration purposes only."
        ),
    }


@app.get("/")
async def root() -> dict:
    return {
        "name": "Eventura AI",
        "description": "Agentic AI Event Planning Platform",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }
