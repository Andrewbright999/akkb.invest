import time
import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.core import get_session
from app.db.repo.users_repo import upsert_user_by_telegram, ensure_account
from app.auth.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class TgAuth(BaseModel):
    id: int
    auth_date: int
    hash: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


def verify_telegram_hash(data: dict, bot_token: str) -> bool:
    """
    Telegram Login Widget:
    secret_key = SHA256(bot_token)
    hash = hex(HMAC_SHA256(data_check_string, secret_key))
    where data_check_string = lines "k=v" sorted by key, excluding 'hash' [web:400].
    """
    received_hash = data.get("hash", "")
    pairs: list[str] = []
    for k, v in data.items():
        if k == "hash" or v is None:
            continue
        pairs.append(f"{k}={v}")
    pairs.sort()
    data_check_string = "\n".join(pairs)

    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_hash, received_hash)


@router.post("/telegram")
async def auth_telegram(payload: TgAuth, session: AsyncSession = Depends(get_session)):
    bot_token = settings.BOT_TOKEN
    if not bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN is not configured")

    data = payload.model_dump()

    # защита от старых логинов
    if int(time.time()) - int(data["auth_date"]) > 86400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram auth expired")  # [web:400]

    # проверка подписи Telegram
    if not verify_telegram_hash(data, bot_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad Telegram hash")  # [web:400]

    # upsert user + ensure account
    telegram_id = int(data["id"])
    user_id = await upsert_user_by_telegram(
        session,
        telegram_id=telegram_id,
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        photo_url=data.get("photo_url"),
    )
    account_id = await ensure_account(session, user_id=user_id)
    await session.commit()

    # JWT
    access_token = create_access_token(sub=str(user_id), ttl_minutes=settings.JWT_EXPIRE_MINUTES)

    return {
        "ok": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "account_id": account_id,
        "profile": {
            "username": data.get("username"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "photo_url": data.get("photo_url"),
        },
    }
