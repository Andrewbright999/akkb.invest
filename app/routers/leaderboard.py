from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.core import get_session
from app.db.repo.leaderboard_repo import get_leaderboard

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard")
async def leaderboard(
    top: int = 10,
    session: AsyncSession = Depends(get_session),
):
    items = await get_leaderboard(session, top=top)
    return {"items": items}
