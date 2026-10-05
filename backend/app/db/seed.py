"""
Database seeder for Eventura AI.

Loads synthetic vendor, availability, and knowledge data from data/ into
the PostgreSQL database. Also computes embeddings for knowledge chunks.

Usage:
    cd eventura/backend
    python -m app.db.seed

Requires the database to be running and migrations to have been applied.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

DATA_DIR = Path(__file__).parents[3] / "data"

async def clear_existing_data(session: AsyncSession) -> None:
    """Remove existing synthetic data before re-seeding."""
    logger.info("Clearing existing synthetic data")

    # Bookings reference vendors, so remove demo bookings first.
    await session.execute(text("DELETE FROM bookings"))

    await session.execute(text("DELETE FROM vendor_availability"))
    await session.execute(text("DELETE FROM knowledge_chunks"))
    await session.execute(text("DELETE FROM vendors WHERE is_synthetic = true"))

    await session.commit()


async def seed_vendors(session: AsyncSession, vendors: list[dict]) -> None:
    from app.db.models import Vendor

    logger.info("Seeding vendors", count=len(vendors))
    for v in vendors:
        vendor = Vendor(
            id=v["id"],
            name=v["name"],
            category=v["category"],
            event_types=v["event_types"],
            city=v["city"],
            state=v["state"],
            base_price=v["base_price"],
            price_per_guest=v.get("price_per_guest"),
            price_floor=v["price_floor"],
            min_capacity=v.get("min_capacity"),
            max_capacity=v.get("max_capacity"),
            rating=v["rating"],
            tags=v["tags"],
            description=v.get("description"),
            contact_email=v.get("contact_email"),
            contact_phone=v.get("contact_phone"),
            min_notice_days=v.get("min_notice_days", 7),
            is_active=v.get("is_active", True),
            is_synthetic=True,
        )
        session.add(vendor)

    await session.commit()
    logger.info("Vendors seeded")


async def seed_availability(session: AsyncSession, records: list[dict]) -> None:
    from app.db.models import VendorAvailability

    logger.info("Seeding availability records", count=len(records))
    # Insert in batches to avoid memory pressure
    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        for r in batch:
            rec = VendorAvailability(
                id=r["id"],
                vendor_id=r["vendor_id"],
                date=r["date"],
                is_available=r["is_available"],
                booked_by_session=r.get("booked_by_session"),
            )
            session.add(rec)
        await session.commit()
        logger.debug("Availability batch committed", batch_end=i + len(batch))

    logger.info("Availability seeded")


async def seed_knowledge(session: AsyncSession, chunks: list[dict]) -> None:
    """Seed knowledge chunks and compute embeddings."""
    from sentence_transformers import SentenceTransformer

    from app.db.models import KnowledgeChunk

    logger.info("Loading embedding model", model=settings.embedding_model)
    embed_model = SentenceTransformer(settings.embedding_model, device="cpu")

    logger.info("Computing embeddings", count=len(chunks))
    texts = [c["content"] for c in chunks]
    embeddings = embed_model.encode(texts, show_progress_bar=True)

    for chunk, embedding in zip(chunks, embeddings):
        kc = KnowledgeChunk(
            id=chunk["id"],
            document_id=chunk["document_id"],
            document_title=chunk["document_title"],
            event_types=chunk["event_types"],
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            metadata_=chunk.get("metadata_", {}),
            embedding=embedding.tolist(),
        )
        session.add(kc)

    await session.commit()
    logger.info("Knowledge chunks seeded with embeddings")


async def run_seed() -> None:
    # Load JSON data (generate if not exists)
    vendors_file = DATA_DIR / "vendors.json"
    availability_file = DATA_DIR / "availability.json"
    chunks_file = DATA_DIR / "knowledge" / "chunks.json"

    if not vendors_file.exists():
        logger.info("Seed JSON files not found — generating now")
        # Run the generator
        sys.path.insert(0, str(DATA_DIR))
        from seed import main as generate  # type: ignore
        generate()

    vendors = json.loads(vendors_file.read_text())
    availability = json.loads(availability_file.read_text())
    chunks = json.loads(chunks_file.read_text())

    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSession_ = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSession_() as session:
        await clear_existing_data(session)
        await seed_vendors(session, vendors)
        await seed_availability(session, availability)
        await seed_knowledge(session, chunks)

    await engine.dispose()
    logger.info("Database seeding complete")


if __name__ == "__main__":
    asyncio.run(run_seed())
