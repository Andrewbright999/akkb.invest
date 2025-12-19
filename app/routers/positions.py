from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.core import get_session
from app.auth.deps import get_current_user
from app.db.models import Position, Instrument

router = APIRouter(tags=["positions"])

@router.get("/positions/{secid}")
async def get_my_position(
    secid: str,
    session: AsyncSession = Depends(get_session),
    user_acc=Depends(get_current_user),
):
    user, acc = user_acc

    q = (
        select(Position.qty, Position.avg_price)
        .select_from(Position)
        .join(Instrument, Instrument.id == Position.instrument_id)
        .where(
            Position.account_id == acc.id,
            Instrument.secid == secid.upper(),
            Instrument.board == "TQBR",
        )
        .limit(1)
    )
    row = (await session.execute(q)).first()

    if not row:
        return {"secid": secid.upper(), "qty": 0.0, "avg_price": 0.0}

    qty, avg_price = row
    return {"secid": secid.upper(), "qty": float(qty), "avg_price": float(avg_price or 0.0)}
