"""
pgvector-based knowledge retrieval for Eventura AI.

Retrieves planning guidelines, checklists, policies, and domain knowledge
from the knowledge_chunks table using cosine similarity on 384-dim embeddings.

This is the semantic retrieval half of the RAG pipeline.
SQL retrieval handles vendor data; this handles unstructured knowledge.
"""

from __future__ import annotations

from sqlalchemy import select, text, bindparam
from sqlalchemy.dialects.postgresql import ARRAY, VARCHAR
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeChunk
from app.logger import get_logger
from app.retrieval.embeddings import embed_text
from app.retrieval.evidence import Evidence, make_evidence

logger = get_logger(__name__)


async def retrieve_knowledge(
    db: AsyncSession,
    session_id: str,
    query: str,
    event_types: list[str] | None = None,
    top_k: int = 5,
    retrieval_round: int = 0,
    min_score: float = 0.25,
) -> list[dict]:
    """
    Retrieve the top-k most relevant knowledge chunks via pgvector cosine search.

    Parameters
    ----------
    db:
        Async SQLAlchemy session.
    session_id:
        For evidence ID scoping.
    query:
        Natural language query.
    event_types:
        Filter by event type (e.g. ["wedding", "general"]).
    top_k:
        Number of results to return.
    retrieval_round:
        0 = initial, 1-2 = re-retrieval.
    min_score:
        Minimum cosine similarity threshold.

    Returns
    -------
    List of dicts with keys: evidence_id, document_id, document_title,
    content, score, query, retrieval_round.
    """
    logger.debug(
        "pgvector knowledge retrieval",
        query=query[:80],
        event_types=event_types,
        top_k=top_k,
        round=retrieval_round,
    )

    # Compute query embedding (deterministic)
    query_embedding = embed_text(query)

    # Build pgvector query — cosine distance operator: <=>
    # Filter by event_type overlap if specified
    if event_types:
        # ANY overlap between chunk.event_types and provided list
        type_filter = "AND (kc.event_types && CAST(:event_types AS varchar[]))"
        params: dict = {
            "query_vec": str(query_embedding),
            "top_k": top_k,
            "event_types": event_types,
        }
    else:
        type_filter = ""
        params = {
            "query_vec": str(query_embedding),
            "top_k": top_k,
        }

    sql = text(f"""
        SELECT
            kc.id,
            kc.document_id,
            kc.document_title,
            kc.event_types,
            kc.chunk_index,
            kc.content,
            1 - (kc.embedding <=> CAST(:query_vec AS vector)) AS score
        FROM knowledge_chunks kc
        WHERE kc.embedding IS NOT NULL
        {type_filter}
        ORDER BY kc.embedding <=> CAST(:query_vec AS vector)        
        LIMIT :top_k
    """)
    sql = sql.bindparams(
    bindparam("event_types", type_=ARRAY(VARCHAR))
    )

    result = await db.execute(sql, params)
    rows = result.fetchall()

    logger.debug("pgvector retrieval results", count=len(rows))

    retrieved = []
    for row in rows:
        score = float(row.score) if row.score is not None else 0.0
        if score < min_score:
            continue

        evidence = make_evidence(
            session_id=session_id,
            source_type="knowledge_pgvector",
            source_ref=row.document_id,
            content=row.content,
            score=score,
            query=query,
            retrieval_round=retrieval_round,
            metadata={
                "document_id": row.document_id,
                "document_title": row.document_title,
                "chunk_index": row.chunk_index,
                "event_types": list(row.event_types),
            },
        )

        retrieved.append({
            "evidence_id": evidence.evidence_id,
            "document_id": row.document_id,
            "document_title": row.document_title,
            "content": row.content,
            "score": round(score, 4),
            "query": query,
            "retrieval_round": retrieval_round,
            "evidence": evidence,
        })

    return retrieved


async def retrieve_knowledge_basic(
    db: AsyncSession,
    session_id: str,
    query: str,
    event_types: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Basic RAG: fixed top-k retrieval with no query refinement.
    Used as the basic-RAG baseline.
    """
    return await retrieve_knowledge(
        db=db,
        session_id=session_id,
        query=query,
        event_types=event_types,
        top_k=top_k,
        retrieval_round=0,
    )
