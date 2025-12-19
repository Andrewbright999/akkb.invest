import asyncio
from app.db.core import engine
from app.db.models import Base
from sqlalchemy.ext.asyncio import AsyncEngine

async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # create_all паттерн [web:267]

if __name__ == "__main__":
    asyncio.run(init_db(engine))
