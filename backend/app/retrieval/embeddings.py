"""
Embedding service for Eventura AI.

Uses sentence-transformers to produce 384-dim vectors (all-MiniLM-L6-v2).
The model is loaded once at process startup and reused.

All arithmetic here is deterministic — no LLM involvement.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    """Load the embedding model once and cache it."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model", model=settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Embedding model loaded")
    return model


def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns a 384-dim float list."""
    model = _get_model()
    vec: np.ndarray = model.encode(text, convert_to_numpy=True)
    return vec.tolist()


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed a batch of texts. More efficient than repeated embed_text calls."""
    model = _get_model()
    vecs: np.ndarray = model.encode(list(texts), convert_to_numpy=True)
    return vecs.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Deterministic cosine similarity — no LLM."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))
