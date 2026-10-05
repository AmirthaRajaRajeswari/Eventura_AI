import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import Vendor


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Vendor)
            .where(Vendor.category == "venue")
            .where(Vendor.city.ilike("%Chennai%"))
        )

        for vendor in result.scalars():
            print(
                f"{vendor.name} | "
                f"price={vendor.base_price} | "
                f"capacity={vendor.min_capacity}-{vendor.max_capacity}"
            )


if __name__ == "__main__":
    asyncio.run(main())