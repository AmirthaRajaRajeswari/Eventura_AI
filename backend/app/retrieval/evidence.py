"""
Evidence tracking for Eventura AI.

Every retrieved item gets a deterministic evidence ID (EV-NNN).
Evidence IDs are stored in the session state so the Critic can verify
that claims are grounded in actual retrieved records.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Literal


SourceType = Literal["vendor_sql", "knowledge_pgvector", "availability", "weather", "tool"]


@dataclass
class Evidence:
    """A single retrieved piece of evidence."""
    evidence_id: str          # e.g. "EV-001"
    source_type: SourceType
    source_ref: str           # e.g. vendor_id or document_id
    content: str              # raw retrieved content (truncated for state)
    score: float              # relevance score 0-1
    query: str                # query used to retrieve this
    retrieval_round: int      # 0 = initial, 1 = first re-retrieval, 2 = second
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "content": self.content[:500],  # truncate for state storage
            "score": round(self.score, 4),
            "query": self.query,
            "retrieval_round": self.retrieval_round,
            "metadata": self.metadata,
        }


class EvidenceRegistry:
    """
    Thread-safe per-session evidence counter.
    Each session gets its own independent ID sequence.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}

    def next_id(self, session_id: str) -> str:
        with self._lock:
            count = self._counters.get(session_id, 0) + 1
            self._counters[session_id] = count
            return f"EV-{count:03d}"

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._counters.pop(session_id, None)


# Module-level singleton
evidence_registry = EvidenceRegistry()


def make_evidence(
    session_id: str,
    source_type: SourceType,
    source_ref: str,
    content: str,
    score: float,
    query: str,
    retrieval_round: int = 0,
    metadata: dict | None = None,
) -> Evidence:
    """Create an Evidence record and assign it a session-scoped ID."""
    ev_id = evidence_registry.next_id(session_id)
    return Evidence(
        evidence_id=ev_id,
        source_type=source_type,
        source_ref=source_ref,
        content=content,
        score=score,
        query=query,
        retrieval_round=retrieval_round,
        metadata=metadata or {},
    )
