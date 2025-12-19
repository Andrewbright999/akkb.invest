from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, User, Position, Instrument, Candle


async def get_leaderboard(
    session: AsyncSession,
    *,
    top: int = 10,
    board: str = "TQBR",
    interval: int = 24,
) -> list[dict]:
    top = max(1, min(int(top), 100))

    # 1) last price по каждому secid (берём последнюю свечу по d)
    latest = (
        select(
            Candle.secid.label("secid"),
            func.max(Candle.d).label("max_d"),
        )
        .where(Candle.board == board, Candle.interval == interval)
        .group_by(Candle.secid)
        .subquery()
    )

    q_last = (
        select(Candle.secid, Candle.close)
        .join(
            latest,
            (Candle.secid == latest.c.secid) & (Candle.d == latest.c.max_d),
        )
        .where(Candle.board == board, Candle.interval == interval)
    )
    last_rows = (await session.execute(q_last)).all()
    last_by_secid = {secid: float(close) for secid, close in last_rows}

    # 2) все позиции: account_id, secid, qty
    q_pos = (
        select(Position.account_id, Instrument.secid, Position.qty)
        .select_from(Position)
        .join(Instrument, Instrument.id == Position.instrument_id)
        .where(Instrument.board == board)
    )
    pos_rows = (await session.execute(q_pos)).all()

    positions_value_by_acc: dict[int, float] = {}
    for account_id, secid, qty in pos_rows:
        qty = float(qty or 0.0)
        if qty <= 0:
            continue
        last = last_by_secid.get(secid, 0.0)
        positions_value_by_acc[account_id] = positions_value_by_acc.get(account_id, 0.0) + qty * last

    # 3) аккаунты + юзеры
    q_acc = (
        select(
            Account.id,
            Account.cash,
            User.username,
            User.first_name,
            User.last_name,
            User.photo_url,
        )
        .select_from(Account)
        .join(User, User.id == Account.user_id)
    )
    acc_rows = (await session.execute(q_acc)).all()

    items = []
    for acc_id, cash, username, first_name, last_name, photo_url in acc_rows:
        cash = float(cash or 0.0)
        pv = float(positions_value_by_acc.get(acc_id, 0.0))
        equity = cash + pv
        items.append({
            "account_id": acc_id,
            "equity": equity,
            "cash": cash,
            "user": {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "photo_url": photo_url,
            }
        })

    # 4) сортировка и rank
    items.sort(key=lambda x: x["equity"], reverse=True)
    out = []
    for i, it in enumerate(items[:top], start=1):
        out.append({
            "rank": i,
            "equity": it["equity"],
            "cash": it["cash"],
            "user": it["user"],
        })
    return out
