from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Optional

import httpx


ISS_BASE = "https://iss.moex.com/iss"

MOEX_MOEXBC_CONSTITUENTS_URL = "https://www.moex.com/en/index/MOEXBC/constituents"

MOEXBC_TQBR_SECIDS: list[str] = [
    "SBER", "GAZP", "LKOH", "ROSN", "NVTK",
    "GMKN", "PLZL", "TATN", "SNGS", "MTSS",
    "MGNT", "ALRS", "NLMK", "CHMF", "PHOR",
]


def _rows_to_dicts(block: dict) -> list[dict]:
    cols = block["columns"]
    return [dict(zip(cols, row)) for row in block["data"]]


@dataclass(frozen=True)
class MoexIssClient:
    """
    Мини-клиент MOEX ISS под 'stock/shares/TQBR'.
    """

    http: httpx.AsyncClient

    async def list_tqbr_shares(self, limit: int = 100, start: int = 0) -> list[dict]:
        """
        Список бумаг на доске TQBR.
        """
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities.json"
        params = {
            "iss.meta": "off",
            "iss.only": "securities",
            "securities.columns": "SECID,SHORTNAME,NAME,ISIN,LOTSIZE,FACEUNIT,SECNAME",
            "limit": limit,
            "start": start,
        }
        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()
        return _rows_to_dicts(payload["securities"])

    async def last_prices_tqbr(self, secids: Optional[Iterable[str]] = None, limit: int = 100, start: int = 0) -> list[dict]:
        """
        Последние цены (не real-time) либо:
        - по всем бумагам на TQBR (страницами limit/start),
        - либо по списку SECID (через параметр securities=...).
        """
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities.json"
        params: dict[str, Any] = {
            "iss.meta": "off",
            "iss.only": "marketdata",
            "marketdata.columns": "SECID,BOARDID,LAST,LASTTOPREVPRICE,VALTODAY,VOLTODAY,UPDATETIME",
            "limit": limit,
            "start": start,
        }
        if secids:
            params["securities"] = ",".join(secids)

        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()
        return _rows_to_dicts(payload["marketdata"])

    async def candles_tqbr(
        self,
        secid: str,
        date_from: date,
        date_to: date,
        interval: int = 24,
    ) -> list[dict]:
        """
        Исторические свечи через history endpoint.
        interval в MOEX candles обычно задают числом (часто 24 = день).
        """
        url = f"{ISS_BASE}/history/engines/stock/markets/shares/boards/TQBR/securities/{secid}.json"
        params = {
            "iss.meta": "off",
            "iss.only": "candles",
            "from": date_from.isoformat(),
            "till": date_to.isoformat(),
            "interval": interval,
        }
        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()
        return _rows_to_dicts(payload["candles"])

    async def marketdata_page_tqbr(self, limit: int = 200, start: int = 0) -> list[dict]:
        """
        Одна страница marketdata по всем бумагам TQBR.
        """
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities.json"
        params: dict[str, Any] = {
            "iss.meta": "off",
            "iss.only": "marketdata",
            "marketdata.columns": "SECID,BOARDID,LAST,VALTODAY,VOLTODAY,UPDATETIME,SYSTIME",
            "limit": limit,
            "start": start,
        }
        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()
        return _rows_to_dicts(payload["marketdata"])
    
    async def securities_info_tqbr(self, secids: Iterable[str]) -> list[dict]:
        """
        Возвращает описания бумаг (имя/короткое имя/ISIN/лот) для списка тикеров.
        Берём именно TQBR, чтобы совпадало с котировками.
        """
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities.json"
        params: dict[str, Any] = {
            "iss.meta": "off",
            "iss.only": "securities",
            "securities": ",".join([s.strip().upper() for s in secids]),
            "securities.columns": "SECID,SHORTNAME,NAME,ISIN,LOTSIZE,FACEUNIT",
        }
        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()
        return _rows_to_dicts(payload["securities"])
    
    async def candles_tqbr(
        self,
        secid: str,
        date_from: date,
        date_to: date,
        interval: int = 24,
        start: int = 0,
    ) -> list[dict]:
        """
        Свечи по бумаге на TQBR.

        В moexer примеры используют путь:
        engines/stock/markets/shares/boards/TQBR/securities/SBER/candles.json
        и секция ответа называется 'candles'. [web:91]
        """
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities/{secid}/candles.json"
        params: dict[str, Any] = {
            "iss.meta": "off",
            "from": date_from.isoformat(),
            "till": date_to.isoformat(),
            "interval": interval,
            "start": start,
        }

        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()

        # защита от "нет candles"
        candles_block = payload.get("candles")
        if candles_block is None:
            # если ISS вернул ошибку/другую секцию — покажем в исключении
            raise ValueError(f"ISS response has no 'candles'. Keys={list(payload.keys())}. Payload={payload}")

        return _rows_to_dicts(candles_block)

    async def candles_tqbr(
        self,
        secid: str,
        date_from: date,
        date_to: date,
        interval: int = 24,
        start: int = 0,
    ) -> list[dict]:
        """
        Свечи по бумаге на TQBR.

        В moexer примеры используют путь:
        engines/stock/markets/shares/boards/TQBR/securities/SBER/candles.json
        и секция ответа называется 'candles'. [web:91]
        """
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities/{secid}/candles.json"
        params: dict[str, Any] = {
            "iss.meta": "off",
            "from": date_from.isoformat(),
            "till": date_to.isoformat(),
            "interval": interval,
            "start": start,
        }

        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()

        # защита от "нет candles"
        candles_block = payload.get("candles")
        if candles_block is None:
            # если ISS вернул ошибку/другую секцию — покажем в исключении
            raise ValueError(f"ISS response has no 'candles'. Keys={list(payload.keys())}. Payload={payload}")

        return _rows_to_dicts(candles_block)    
    
    async def candles_tqbr_page(self, secid: str, date_from: date, date_to: date, interval: int, start: int) -> list[dict]:
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities/{secid}/candles.json"
        params: dict[str, Any] = {
            "iss.meta": "off",
            "from": date_from.isoformat(),
            "till": date_to.isoformat(),
            "interval": interval,
            "start": start,  # пагинация как в примерах [web:91]
        }
        r = await self.http.get(url, params=params)
        r.raise_for_status()
        payload = r.json()
        block = payload.get("candles")
        return _rows_to_dicts(block) if block else []

    async def candles_tqbr_all(self, secid: str, date_from: date, date_to: date, interval: int, page_size: int = 500, max_pages: int = 200) -> list[dict]:
        all_rows: list[dict] = []
        for page in range(max_pages):
            start = page * page_size
            chunk = await self.candles_tqbr_page(secid, date_from, date_to, interval, start=start)
            if not chunk:
                break
            all_rows.extend(chunk)
            # если пришло меньше page_size — дальше данных нет
            if len(chunk) < page_size:
                break
        return all_rows
