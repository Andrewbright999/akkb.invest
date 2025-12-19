from app.services.moex_iss import MoexIssClient

from typing import Any

def _to_float(x: Any) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _is_valid_last(x: Any) -> bool:
    try:
        return x is not None and float(x) > 0
    except (TypeError, ValueError):
        return False


async def popular_today_by_valtoday(
    moex: MoexIssClient,
    top_n: int = 15,
    page_limit: int = 200,
    max_pages: int = 30,
) -> list[dict]:
    # 1) Собираем marketdata страницами
    rows: list[dict] = []
    for page in range(max_pages):
        start = page * page_limit
        chunk = await moex.marketdata_page_tqbr(limit=page_limit, start=start)
        if not chunk:
            break
        rows.extend(chunk)

    # 2) Дедуп: выбираем "лучшую" строку для каждого SECID
    best_by_secid: dict[str, dict] = {}

    for r in rows:
        secid = (r.get("SECID") or "").strip().upper()
        if not secid:
            continue

        candidate = {
            "secid": secid,
            "boardid": r.get("BOARDID"),
            "last": _to_float(r.get("LAST")),
            "valtoday": _to_float(r.get("VALTODAY")),
            "voltoday": _to_float(r.get("VOLTODAY")),
            "time": r.get("UPDATETIME") or r.get("SYSTIME"),
        }

        # отсекаем мусор: нет цены => не надо в "популярное"
        if not _is_valid_last(candidate["last"]):
            continue

        prev = best_by_secid.get(secid)
        if prev is None:
            best_by_secid[secid] = candidate
            continue

        # сравнение: больше valtoday => лучше
        if candidate["valtoday"] > prev["valtoday"]:
            best_by_secid[secid] = candidate

    # 3) Топ-N по обороту
    items = list(best_by_secid.values())
    items.sort(key=lambda x: x["valtoday"], reverse=True)
    return items[:top_n]

