from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Position, Trade, Instrument, Candle


async def _get_instrument(session: AsyncSession, secid: str, board: str = "TQBR") -> Instrument:
    secid = secid.upper()
    q = select(Instrument).where(Instrument.secid == secid, Instrument.board == board)
    inst = (await session.execute(q)).scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail=f"Instrument not found: {secid}")
    return inst


async def _get_last_price(session: AsyncSession, secid: str, board: str = "TQBR", interval: int = 24) -> float:
    secid = secid.upper()
    q = (
        select(Candle.close)
        .where(Candle.secid == secid, Candle.board == board, Candle.interval == interval)
        .order_by(Candle.d.desc())   # "последняя" по дате [web:539]
        .limit(1)
    )
    last = (await session.execute(q)).scalar_one_or_none()
    if last is None:
        raise HTTPException(
            status_code=404,
            detail=f"No candles in DB for {secid} ({board}, interval={interval}). Load candles first.",
        )
    return float(last)


async def buy(
    session: AsyncSession,
    *,
    account_id: int,
    secid: str,
    qty: float,
    price: float | None,
    board: str = "TQBR",
):
    if qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")

    inst = await _get_instrument(session, secid, board=board)
    px = float(price) if price is not None else await _get_last_price(session, secid, board=board)
    if px <= 0:
        raise HTTPException(status_code=400, detail="price must be > 0")

    # account
    acc = (await session.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    cost = qty * px
    if acc.cash < cost:
        raise HTTPException(status_code=400, detail=f"Not enough cash: need {cost}, have {acc.cash}")

    # position
    pos = (await session.execute(
        select(Position).where(
            Position.account_id == account_id,
            Position.instrument_id == inst.id,
        )
    )).scalar_one_or_none()

    if pos is None:
        pos = Position(account_id=account_id, instrument_id=inst.id, qty=0.0, avg_price=0.0)
        session.add(pos)
        await session.flush()

    new_qty = float(pos.qty) + float(qty)
    new_avg = ((float(pos.qty) * float(pos.avg_price)) + (float(qty) * px)) / new_qty if new_qty > 0 else 0.0
    pos.qty = new_qty
    pos.avg_price = new_avg

    acc.cash = float(acc.cash) - cost

    session.add(Trade(
        account_id=account_id,
        instrument_id=inst.id,
        side="BUY",
        qty=float(qty),
        price=px,
    ))


async def sell(
    session: AsyncSession,
    *,
    account_id: int,
    secid: str,
    qty: float,
    price: float | None,
    board: str = "TQBR",
):
    if qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")

    inst = await _get_instrument(session, secid, board=board)
    px = float(price) if price is not None else await _get_last_price(session, secid, board=board)
    if px <= 0:
        raise HTTPException(status_code=400, detail="price must be > 0")

    acc = (await session.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    pos = (await session.execute(
        select(Position).where(
            Position.account_id == account_id,
            Position.instrument_id == inst.id,
        )
    )).scalar_one_or_none()

    if pos is None or float(pos.qty) < float(qty):
        raise HTTPException(status_code=400, detail="Not enough position qty to sell")

    pos.qty = float(pos.qty) - float(qty)
    if pos.qty == 0:
        pos.avg_price = 0.0

    acc.cash = float(acc.cash) + (float(qty) * px)

    session.add(Trade(
        account_id=account_id,
        instrument_id=inst.id,
        side="SELL",
        qty=float(qty),
        price=px,
    ))
