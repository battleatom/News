import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OUT = "markets.json"
SYMBOLS = [
    ("S&P 500", "SPY", "fund"),
    ("DOW", "DIA", "fund"),
    ("NASDAQ", "QQQ", "fund"),
    ("VIX", "^VIX", "index"),
    ("WTI OIL", "CL=F", "commodity"),
    ("GOLD", "GC=F", "commodity"),
    ("10Y", "^TNX", "index"),
]


def get_market(symbol):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?range=1d&interval=1m"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NewsBrief/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read())
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        raise RuntimeError("No Yahoo Finance result")
    meta = result[0].get("meta") or {}
    price = meta.get("regularMarketPrice")
    previous = meta.get("previousClose", meta.get("chartPreviousClose"))
    if price is None:
        raise RuntimeError("Missing market price")
    pct = ((price - previous) / previous * 100) if previous else 0
    return {
        "symbol": symbol,
        "price": price,
        "previousClose": previous,
        "changePct": pct,
        "marketState": meta.get("marketState", "UNKNOWN"),
        "currency": meta.get("currency", "USD"),
        "updated": meta.get("regularMarketTime"),
    }


def main():
    markets = []
    for name, symbol, kind in SYMBOLS:
        try:
            value = get_market(symbol)
            value.update({"name": name, "kind": kind})
            markets.append(value)
            print(name, value["price"])
        except Exception as exc:
            print(f"{name}: {exc}")
            markets.append({"name": name, "symbol": symbol, "kind": kind, "error": str(exc)})

    spy = next((m for m in markets if m["symbol"] == "SPY" and "error" not in m), None)
    regular_closed = bool(spy and spy.get("marketState") == "CLOSED")
    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "marketClosed": regular_closed,
        "source": "Yahoo Finance chart endpoint",
        "markets": markets,
        "opec": {"name": "OPEC", "status": "WATCH"},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
