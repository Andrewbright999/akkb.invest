from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert as mysql_insert
from app.db.models import User, Account

async def upsert_user_by_telegram(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    photo_url: str | None,
) -> int:
    stmt = mysql_insert(User).values({
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "photo_url": photo_url,
    })
    stmt = stmt.on_duplicate_key_update(
        username=stmt.inserted.username,
        first_name=stmt.inserted.first_name,
        last_name=stmt.inserted.last_name,
        photo_url=stmt.inserted.photo_url,
    )
    await session.execute(stmt)

    q = select(User.id).where(User.telegram_id == telegram_id)
    return (await session.execute(q)).scalar_one()

async def ensure_account(session: AsyncSession, user_id: int) -> int:
    stmt = mysql_insert(Account).values({"user_id": user_id})
    stmt = stmt.on_duplicate_key_update(user_id=stmt.inserted.user_id)
    await session.execute(stmt)

    q = select(Account.id).where(Account.user_id == user_id)
    return (await session.execute(q)).scalar_one()
