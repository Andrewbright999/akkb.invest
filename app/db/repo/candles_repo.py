from __future__ import annotations
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert as mysql_insert  # upsert MySQL [web:268]

from app.db.models import Instrument
from app.db.models import Candle, CandleCache


async def upsert_candles(session: AsyncSession, secid: str, board: str, interval: int, rows: list[dict]) -> None:
    if not rows:
        return

    values = []
    for r in rows:
        # ожидаем нормализованные ключи: t(open/high/low/close/volume)
        d = date.fromisoformat(r["t"][:10])
        values.append({
            "secid": secid,
            "board": board,
            "interval": interval,
            "d": d,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r["volume"]) if r.get("volume") is not None else None,
            "updated_at": datetime.utcnow(),
        })

    stmt = mysql_insert(Candle).values(values)
    stmt = stmt.on_duplicate_key_update(  # MySQL upsert [web:268]
        open=stmt.inserted.open,
        high=stmt.inserted.high,
        low=stmt.inserted.low,
        close=stmt.inserted.close,
        volume=stmt.inserted.volume,
        updated_at=stmt.inserted.updated_at,
    )
    await session.execute(stmt)


async def mark_cache_range(session: AsyncSession, secid: str, board: str, interval: int, date_from: date, date_to: date) -> None:
    stmt = mysql_insert(CandleCache).values({
        "secid": secid, "board": board, "interval": interval,
        "date_from": date_from, "date_to": date_to,
        "updated_at": datetime.utcnow(),
    }).on_duplicate_key_update(updated_at=datetime.utcnow())  # [web:268]
    await session.execute(stmt)


async def cache_is_fresh(session: AsyncSession, secid: str, board: str, interval: int, date_from: date, date_to: date, ttl_minutes: int = 60) -> bool:
    q = select(CandleCache.updated_at).where(
        CandleCache.secid == secid,
        CandleCache.board == board,
        CandleCache.interval == interval,
        CandleCache.date_from == date_from,
        CandleCache.date_to == date_to,
    )
    updated_at = (await session.execute(q)).scalar_one_or_none()
    if not updated_at:
        return False
    return updated_at >= (datetime.utcnow() - timedelta(minutes=ttl_minutes))


async def read_candles(session: AsyncSession, secid: str, board: str, interval: int, date_from: date, date_to: date) -> list[dict]:
    q = (
        select(Candle.d, Candle.open, Candle.high, Candle.low, Candle.close, Candle.volume)
        .where(
            Candle.secid == secid,
            Candle.board == board,
            Candle.interval == interval,
            Candle.d >= date_from,
            Candle.d <= date_to,
        )
        .order_by(Candle.d.asc())
    )
    res = await session.execute(q)
    out = []
    for d, o, h, l, c, v in res.all():
        out.append({"t": d.isoformat(), "open": o, "high": h, "low": l, "close": c, "volume": v})
    return out

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
