from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.core import get_session
from app.auth.deps import get_current_user
from app.db.repo.portfolio_repo import get_portfolio

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
async def portfolio(
    session: AsyncSession = Depends(get_session),
    user_acc=Depends(get_current_user),
):
    user, acc = user_acc
    return await get_portfolio(session, account_id=acc.id)
