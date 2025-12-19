from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Position, Instrument, Candle


async def _get_last_price(
    session: AsyncSession,
    secid: str,
    board: str = "TQBR",
    interval: int = 24,
) -> float:
    q = (
        select(Candle.close)
        .where(Candle.secid == secid.upper(), Candle.board == board, Candle.interval == interval)
        .order_by(Candle.d.desc())
        .limit(1)
    )
    last = (await session.execute(q)).scalar_one_or_none()
    if last is None:
        raise HTTPException(status_code=404, detail=f"No candles in DB for {secid} ({board}, interval={interval})")
    return float(last)


async def get_portfolio(
    session: AsyncSession,
    *,
    account_id: int,
    board: str = "TQBR",
    interval: int = 24,
) -> dict:
    acc = (await session.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    q = (
        select(
            Position.qty,
            Position.avg_price,
            Instrument.secid,
            Instrument.name,
        )
        .select_from(Position)
        .join(Instrument, Instrument.id == Position.instrument_id)
        .where(Position.account_id == account_id)
        .order_by(Instrument.secid.asc())
    )
    rows = (await session.execute(q)).all()

    positions: list[dict] = []

    total_cost = 0.0
    positions_value = 0.0

    for qty, avg_price, secid, name in rows:
        qty = float(qty or 0.0)
        if qty <= 0:
            continue

        avg_price = float(avg_price or 0.0)
        last = await _get_last_price(session, secid, board=board, interval=interval)

        cost = qty * avg_price
        value = qty * float(last)

        pnl_rub = value - cost
        pnl_pct = (pnl_rub / cost * 100.0) if cost > 0 else 0.0

        total_cost += cost
        positions_value += value

        positions.append({
            "secid": secid,
            "name": name or secid,
            "qty": qty,
            "avg_price": avg_price,
            "last": float(last),

            "cost": float(cost),
            "value": float(value),

            "pnl_rub": float(pnl_rub),
            "pnl_pct": float(pnl_pct),
        })

    cash = float(acc.cash or 0.0)

    positions_pnl_rub = positions_value - total_cost
    positions_pnl_pct = (positions_pnl_rub / total_cost * 100.0) if total_cost > 0 else 0.0
    equity = cash + positions_value

    return {
        "account": {"id": acc.id, "cash": cash},
        "summary": {
            "total_cost": float(total_cost),
            "positions_value": float(positions_value),
            "positions_pnl_rub": float(positions_pnl_rub),
            "positions_pnl_pct": float(positions_pnl_pct),
            "equity": float(equity),
        },
        "positions": positions,
    }
