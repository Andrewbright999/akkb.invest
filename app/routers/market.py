from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.core import get_session
from app.deps import moex

from app.db.repo.candles_repo import (
    cache_is_fresh, read_candles, upsert_candles, mark_cache_range
)

from app.services.popular_by_turnover import popular_today_by_valtoday
from app.db.repo.instruments_repo import (
    upsert_instruments, is_instruments_cache_fresh, get_instrument
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/popular-today")
async def popular_today(
    top: int = 15,
    session: AsyncSession = Depends(get_session),
):
    board = "TQBR"

    # 1) котировки/оборот (из MOEX)
    quotes = await popular_today_by_valtoday(moex, top_n=top)  # [{secid,last,valtoday,...}]
    secids = [q["secid"] for q in quotes]

    # 2) если справочник не свежий — обновим
    if not await is_instruments_cache_fresh(session, max_age_hours=24):
        info = await moex.securities_info_tqbr(secids)  # [{SECID,NAME,SHORTNAME,ISIN,LOTSIZE...}]
        await upsert_instruments(session, board=board, rows=info)
        await session.commit()

    # 3) склеим
    items = []
    for q in quotes:
        inst = await get_instrument(session, q["secid"], board=board)
        items.append({
            "secid": q["secid"],
            "name": (inst["name"] if inst else q["secid"]),
            "last": q.get("last"),
            "valtoday": q.get("valtoday"),
            "time": q.get("time"),
        })

    return {"items": items}


def downsample(items: list[dict], max_points: int = 1500) -> list[dict]:
    n = len(items)
    if n <= max_points:
        return items
    step = max(1, n // max_points)
    return items[::step]


@router.get("/candles/{secid}")
async def candles(
    secid: str,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    interval: int = Query(24),
    max_points: int = Query(1500),
    session: AsyncSession = Depends(get_session),
):
    secid = secid.upper()
    board = "TQBR"

    if await cache_is_fresh(session, secid, board, interval, date_from, date_to, ttl_minutes=60):
        data = await read_candles(session, secid, board, interval, date_from, date_to)
        return {"secid": secid, "candles": downsample(data, max_points=max_points), "source": "db"}

    # 1) тянем из MOEX (пагинация start внутри candles_tqbr_all)
    rows_raw = await moex.candles_tqbr_all(secid, date_from, date_to, interval=interval)

    # 2) нормализуем
    rows_norm = []
    for r in rows_raw:
        t = r.get("begin") or r.get("BEGIN") or r.get("end") or r.get("END")
        if not t:
            continue
        rows_norm.append({
            "t": t,
            "open": r.get("open") if r.get("open") is not None else r.get("OPEN"),
            "high": r.get("high") if r.get("high") is not None else r.get("HIGH"),
            "low": r.get("low") if r.get("low") is not None else r.get("LOW"),
            "close": r.get("close") if r.get("close") is not None else r.get("CLOSE"),
            "volume": r.get("volume") if r.get("volume") is not None else r.get("VOLUME"),
        })

    # 3) сохраняем в MySQL (upsert) + отмечаем кэш
    await upsert_candles(session, secid, board, interval, rows_norm)
    await mark_cache_range(session, secid, board, interval, date_from, date_to)
    await session.commit()

    data = await read_candles(session, secid, board, interval, date_from, date_to)
    return {"secid": secid, "candles": downsample(data, max_points=max_points), "source": "moex->db"}


@router.get("/line/{secid}")
async def line(
    secid: str,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    interval: int = Query(24),
    max_points: int = Query(2000),
    session: AsyncSession = Depends(get_session),
):
    resp = await candles(
        secid,
        date_from=date_from,
        date_to=date_to,
        interval=interval,
        max_points=max_points,
        session=session,
    )
    pts = [{"t": c["t"], "close": c["close"]} for c in resp["candles"]]
    return {"secid": secid.upper(), "points": pts, "source": resp.get("source")}
