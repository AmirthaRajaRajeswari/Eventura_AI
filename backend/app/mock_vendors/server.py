"""
Standalone FastAPI application for the Mock Vendor Marketplace.

Run on a separate port (8001) from the main backend.
The main application communicates with it via HTTP — never via direct import.

Start with:
    uvicorn app.mock_vendors.server:app --port 8001 --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logger import configure_logging
from app.mock_vendors.router import router

configure_logging()

app = FastAPI(
    title="Eventura AI — Mock Vendor Marketplace",
    description=(
        "Synthetic vendor marketplace for demo purposes. "
        "All data is fictional and used for demonstration only."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "mock-vendor-marketplace",
        "disclaimer": (
            "All vendor and pricing data is synthetic and used for "
            "demonstration purposes only."
        ),
    }
