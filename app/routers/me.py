from fastapi import APIRouter, Depends
from app.auth.deps import get_current_user

router = APIRouter(tags=["me"])

@router.get("/me")
async def me(user_acc=Depends(get_current_user)):
    user, acc = user_acc
    return {
        "user": {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "photo_url": user.photo_url,
        },
  "account": { "id": acc.id, "cash": acc.cash }
}

