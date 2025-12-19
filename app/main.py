from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.pages import router as pages_router
from app.routers.market import router as market_router
from app.routers.users import router as users_router
from app.routers.telegram_auth import router as telegram_auth_router
from app.routers.me import router as me_router
from app.routers.market_last import router as market_last_router
from app.routers.trading import router as trading_router
from app.routers.portfolio import router as portfolio_router
from app.routers.positions import router as positions_router
from app.routers.leaderboard import router as leaderboard_router



from app.db.core import engine
from app.db.init_db import init_db

app = FastAPI(title="MOEX Demo")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages_router)
app.include_router(market_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(market_last_router, prefix="/api")
app.include_router(trading_router, prefix="/api")
app.include_router(portfolio_router, prefix="/api")
app.include_router(positions_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")



# auth обычно НЕ под /api, чтобы login.html мог слать POST /auth/telegram
app.include_router(telegram_auth_router)

# выбери один вариант:
app.include_router(me_router, prefix="/api")  # если в me_router нет prefix="/api"
# app.include_router(me_router)              # если prefix уже задан внутри router = APIRouter(prefix="/api")

@app.on_event("startup")
async def _startup():
    await init_db(engine)
