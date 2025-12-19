from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.core import get_session
from app.db.models import CandleCache, Instrument

router = APIRouter(prefix="/market", tags=["market"])

@router.get("/last/{secid}")
async def market_last(secid: str, session: AsyncSession = Depends(get_session)):
    # Берём из CandleCache (у тебя она уже есть), это и есть "последняя" в твоей системе.
    q = await session.execute(
        select(CandleCache).join(Instrument, CandleCache.instrument_id == Instrument.id)
        .where(Instrument.secid == secid, Instrument.board == "TQBR")
    )
    row = q.scalar_one_or_none()
    if row is None or row.close is None:
        raise HTTPException(status_code=404, detail="Last price not found")
    return {"secid": secid, "last": float(row.close)}
