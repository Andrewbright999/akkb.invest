from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["pages"])

@router.get("/")
def index_page():
    return FileResponse("static/index.html")

@router.get("/stock")
def stock_page():
    return FileResponse("static/stock.html")

@router.get("/login")
def stock_page():
    return FileResponse("static/login.html")
