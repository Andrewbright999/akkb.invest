from __future__ import annotations
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.db.models import Instrument

async def upsert_instruments(session: AsyncSession, board: str, rows: list[dict]) -> None:
    if not rows:
        return
    values = []
    for r in rows:
        values.append({
            "secid": (r.get("SECID") or "").upper(),
            "board": board,
            "name": r.get("NAME") or r.get("SHORTNAME") or (r.get("SECID") or ""),
            "shortname": r.get("SHORTNAME") or "",
            "isin": r.get("ISIN") or "",
            "lotsize": int(r.get("LOTSIZE") or 1),
            "updated_at": datetime.utcnow(),
        })

    stmt = mysql_insert(Instrument).values(values)
    stmt = stmt.on_duplicate_key_update(
        name=stmt.inserted.name,
        shortname=stmt.inserted.shortname,
        isin=stmt.inserted.isin,
        lotsize=stmt.inserted.lotsize,
        updated_at=stmt.inserted.updated_at,
    )
    await session.execute(stmt)

async def get_instrument(session: AsyncSession, secid: str, board: str = "TQBR") -> dict | None:
    q = select(Instrument).where(Instrument.secid == secid.upper(), Instrument.board == board)
    obj = (await session.execute(q)).scalar_one_or_none()
    if not obj:
        return None
    return {
        "secid": obj.secid,
        "board": obj.board,
        "name": obj.name,
        "shortname": obj.shortname,
        "isin": obj.isin,
        "lotsize": obj.lotsize,
        "updated_at": obj.updated_at,
    }

async def is_instruments_cache_fresh(session: AsyncSession, max_age_hours: int = 24) -> bool:
    q = select(Instrument.updated_at).order_by(Instrument.updated_at.desc()).limit(1)
    updated_at = (await session.execute(q)).scalar_one_or_none()
    if not updated_at:
        return False
    return updated_at >= (datetime.utcnow() - timedelta(hours=max_age_hours))
