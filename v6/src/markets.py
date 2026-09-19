from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 Underreported-V6/1.0"
TIMEOUT = 18
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()

MARKETS = [
    ("^GSPC", "S&P 500"),
    ("^DJI", "DOW"),
    ("^IXIC", "NASDAQ"),
    ("^RUT", "RUSSELL 2000"),
    ("^VIX", "VIX"),
    ("CL=F", "WTI OIL"),
    ("BZ=F", "BRENT"),
    ("NG=F", "NAT GAS"),
    ("GC=F", "GOLD"),
    ("SI=F", "SILVER"),
    ("HG=F", "COPPER"),
    ("DX-Y.NYB", "U.S. DOLLAR"),
    ("^TNX", "10Y"),
    ("BTC-USD", "BITCOIN"),
    ("ETH-USD", "ETHEREUM"),
]


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.load(response)


def _row(symbol: str, label: str, price: float, prev: float | None, currency: str, market_state: str, source: str) -> dict:
    change = ((float(price) - float(prev)) / float(prev) * 100) if prev else 0
    return {
        "symbol": symbol,
        "label": label,
        "price": round(float(price), 2),
        "previousClose": round(float(prev), 2) if prev is not None else None,
        "changePct": change,
        "currency": currency,
        "marketState": market_state,
        "source": source,
    }


def _yahoo_market(symbol: str, label: str) -> dict:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?range=5d&interval=1d"
    result = ((fetch_json(url).get("chart") or {}).get("result") or [{}])[0]
    meta = result.get("meta") or {}
    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose") or meta.get("regularMarketPreviousClose")
    if price is None:
        closes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
        valid = [x for x in closes if isinstance(x, (int, float))]
        if valid:
            price = valid[-1]
            prev = valid[-2] if len(valid) > 1 else prev
    if price is None:
        raise ValueError("Yahoo returned no market price")
    return _row(symbol, label, float(price), float(prev) if prev is not None else None, meta.get("currency") or "USD", meta.get("marketState") or "", "Yahoo Finance")


def _alpha_series(function: str, extra: dict[str, str] | None = None) -> tuple[float, float | None]:
    if not ALPHA_VANTAGE_API_KEY:
        raise RuntimeError("Alpha Vantage key is not configured")
    params = {"function": function, "apikey": ALPHA_VANTAGE_API_KEY}
    if extra:
        params.update(extra)
    payload = fetch_json("https://www.alphavantage.co/query?" + urllib.parse.urlencode(params))
    if payload.get("Information") or payload.get("Note") or payload.get("Error Message"):
        raise RuntimeError(payload.get("Information") or payload.get("Note") or payload.get("Error Message"))
    valid = []
    for item in payload.get("data") or []:
        try:
            value = float(item.get("value"))
        except (TypeError, ValueError):
            continue
        valid.append(value)
        if len(valid) == 2:
            break
    if not valid:
        raise ValueError("Alpha Vantage returned no usable series values")
    return valid[0], valid[1] if len(valid) > 1 else None


def _alpha_crypto(symbol: str) -> tuple[float, float | None]:
    if not ALPHA_VANTAGE_API_KEY:
        raise RuntimeError("Alpha Vantage key is not configured")
    code = symbol.split("-", 1)[0]
    params = {
        "function": "DIGITAL_CURRENCY_DAILY",
        "symbol": code,
        "market": "USD",
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    payload = fetch_json("https://www.alphavantage.co/query?" + urllib.parse.urlencode(params))
    if payload.get("Information") or payload.get("Note") or payload.get("Error Message"):
        raise RuntimeError(payload.get("Information") or payload.get("Note") or payload.get("Error Message"))
    series = payload.get("Time Series (Digital Currency Daily)") or {}
    closes = []
    for day in sorted(series.keys(), reverse=True):
        item = series.get(day) or {}
        raw = item.get("4. close") or item.get("4a. close (USD)")
        try:
            closes.append(float(raw))
        except (TypeError, ValueError):
            continue
        if len(closes) == 2:
            break
    if not closes:
        raise ValueError("Alpha Vantage returned no usable crypto prices")
    return closes[0], closes[1] if len(closes) > 1 else None


def _alpha_market(symbol: str, label: str) -> dict:
    if symbol == "CL=F":
        price, prev = _alpha_series("WTI", {"interval": "daily"})
    elif symbol == "BZ=F":
        price, prev = _alpha_series("BRENT", {"interval": "daily"})
    elif symbol == "NG=F":
        price, prev = _alpha_series("NATURAL_GAS", {"interval": "daily"})
    elif symbol == "^TNX":
        price, prev = _alpha_series("TREASURY_YIELD", {"interval": "daily", "maturity": "10year"})
    elif symbol in {"BTC-USD", "ETH-USD"}:
        price, prev = _alpha_crypto(symbol)
    else:
        raise RuntimeError("No exact Alpha Vantage fallback for this instrument")
    return _row(symbol, label, price, prev, "USD", "", "Alpha Vantage")


def _collect_market(pair: tuple[str, str]) -> tuple[dict | None, str]:
    symbol,label=pair
    try:return _yahoo_market(symbol,label),""
    except Exception as yahoo_exc:
        if ALPHA_VANTAGE_API_KEY and symbol in {"CL=F","BZ=F","NG=F","^TNX","BTC-USD","ETH-USD"}:
            try:return _alpha_market(symbol,label),""
            except Exception as alpha_exc:return None,f"{symbol}: Yahoo {type(yahoo_exc).__name__}; Alpha {type(alpha_exc).__name__}"
        return None,f"{symbol}: Yahoo {type(yahoo_exc).__name__}"

def collect_markets() -> tuple[list[dict], str]:
    rows=[];errors=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(_collect_market,pair) for pair in MARKETS]
        for future in as_completed(futures):
            row,error=future.result()
            if row:rows.append(row)
            if error:errors.append(error)
    order={symbol:i for i,(symbol,_) in enumerate(MARKETS)}
    rows.sort(key=lambda row:order.get(row.get("symbol",""),999))
    return rows,"; ".join(errors)


def verify_alpha_vantage() -> dict:
    if not ALPHA_VANTAGE_API_KEY:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is not configured")
    params = {"function": "MARKET_STATUS", "apikey": ALPHA_VANTAGE_API_KEY}
    payload = fetch_json("https://www.alphavantage.co/query?" + urllib.parse.urlencode(params))
    if payload.get("Information") or payload.get("Note") or payload.get("Error Message"):
        raise RuntimeError(payload.get("Information") or payload.get("Note") or payload.get("Error Message"))
    markets = payload.get("markets") or []
    if not markets:
        raise RuntimeError("Alpha Vantage verification returned no market status data")
    return {"configured": True, "provider": "Alpha Vantage", "marketStatusCount": len(markets)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-alpha", action="store_true")
    args = parser.parse_args()
    if args.verify_alpha:
        print(json.dumps(verify_alpha_vantage(), indent=2))
    else:
        rows, error = collect_markets()
        print(json.dumps({"markets": rows, "error": error}, indent=2))


if __name__ == "__main__":
    main()
