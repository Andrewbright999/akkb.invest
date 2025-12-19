from fastapi import APIRouter

router = APIRouter(tags=["users"])

# потом: /api/auth, /api/users/me и т.д.
