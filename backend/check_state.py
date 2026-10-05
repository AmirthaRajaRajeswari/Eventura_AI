import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import Session as DBSession

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DBSession).where(
                DBSession.id == "a9260665-c876-4864-b011-c68863b1650a"
            )
        )

        session = result.scalar_one()

        print("STATUS:", session.status)
        print("\nSTATE SNAPSHOT:")
        print(session.state_snapshot)


asyncio.run(main())