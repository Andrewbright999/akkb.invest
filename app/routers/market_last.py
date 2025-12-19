from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.core import get_session
from app.db.models import Candle

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/last/{secid}")
async def market_last(secid: str, session: AsyncSession = Depends(get_session)):
    secid = secid.upper()

    q = (
        select(Candle.close, Candle.d)
        .where(Candle.secid == secid, Candle.board == "TQBR", Candle.interval == 24)
        .order_by(Candle.d.desc())
        .limit(1)
    )
    row = (await session.execute(q)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Last price not found (no candles in DB)")

    close, d = row
    return {"secid": secid, "last": float(close), "date": d.isoformat()}
