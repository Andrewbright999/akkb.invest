import httpx
from app.services.moex_iss import MoexIssClient

_http = httpx.AsyncClient(timeout=20)
moex = MoexIssClient(http=_http)

async def shutdown_http():
    await _http.aclose()
