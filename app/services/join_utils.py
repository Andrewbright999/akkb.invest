
def join_quotes_with_names(quotes: list[dict], securities: list[dict]) -> list[dict]:
    by_secid = {s["SECID"].upper(): s for s in securities if s.get("SECID")}
    out = []
    for q in quotes:
        secid = (q.get("secid") or q.get("SECID") or "").upper()
        s = by_secid.get(secid, {})
        out.append({
            "secid": secid,
            "name": s.get("NAME") or s.get("SHORTNAME") or secid,
            "shortname": s.get("SHORTNAME"),
            "isin": s.get("ISIN"),
            "lotsize": s.get("LOTSIZE"),
            "last": q.get("last") or q.get("LAST"),
            "valtoday": q.get("valtoday") or q.get("VALTODAY"),
            "voltoday": q.get("voltoday") or q.get("VOLTODAY"),
            "time": q.get("time") or q.get("UPDATETIME"),
        })
    return out

