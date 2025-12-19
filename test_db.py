import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL='mysql+aiomysql://akkb:akkb@127.0.0.1:3306/akkb'


async def main():
    engine = create_async_engine(os.environ["DB_URL"])
    # engine = create_async_engine(DB_URL)
    
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT 1"))
        print("OK:", r.scalar_one())
    await engine.dispose()

asyncio.run(main())
