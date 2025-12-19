from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.core import get_session
from app.auth.deps import get_current_user
from app.db.repo.trading import buy, sell

router = APIRouter(prefix="/trade", tags=["trade"])


# app/routers/trading.py
from pydantic import BaseModel, Field

class TradeRequest(BaseModel):
    secid: str = Field(..., min_length=1)
    qty: float = Field(..., gt=0)

    class Config:
        extra = "forbid"

@router.post("/buy")
async def trade_buy(
    body: TradeRequest,
    session: AsyncSession = Depends(get_session),
    user_acc=Depends(get_current_user),
):
    user, acc = user_acc
    await buy(session, account_id=acc.id, secid=body.secid, price=None, qty=body.qty)
    await session.commit()
    return {"ok": True}


@router.post("/sell")
async def trade_sell(
    body: TradeRequest,
    session: AsyncSession = Depends(get_session),
    user_acc=Depends(get_current_user),
):
    user, acc = user_acc
    await sell(session, account_id=acc.id, secid=body.secid, price=None, qty=body.qty)
    await session.commit()
    return {"ok": True}