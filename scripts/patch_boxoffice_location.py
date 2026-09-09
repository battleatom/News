from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path("boxoffice.json")
MAX_LOCAL_NEWS = 5
STATES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia"
}


def clean(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Underreported/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def state_news(code: str, name: str) -> dict:
    query = urllib.parse.quote(f'("{name}" OR "{code}") (movies OR movie theater OR cinema OR box office) when:14d')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    items = []
    try:
        root = ET.fromstring(fetch(url))
        for item in root.findall(".//item"):
            title = clean(item.findtext("title"))
            link = item.findtext("link") or ""
            if not title or not link:
                continue
            # Skip obvious non-English results.
            if any(0x0400 <= ord(ch) <= 0x052F for ch in title):
                continue
            source = item.find("source")
            items.append({
                "title": title,
                "link": link,
                "description": clean(item.findtext("description")),
                "source": clean(source.text if source is not None else ""),
                "pubDate": clean(item.findtext("pubDate")),
            })
            if len(items) >= MAX_LOCAL_NEWS:
                break
    except Exception as exc:
        print(f"Box Office local feed failed for {name}: {exc}")
    return {"state": code, "stateName": name, "news": items}


def main() -> None:
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    locations = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(state_news, code, name): code for code, name in STATES.items()}
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                locations[code] = fut.result()
            except Exception as exc:
                locations[code] = {"state": code, "stateName": STATES[code], "news": []}
                print(f"Box Office location enrichment failed for {code}: {exc}")

    data["locations"] = locations
    data["locationMode"] = "state-aware"
    data["locationNote"] = "Movie releases are national; local movie news is selected by the visitor's detected U.S. state. Farmington showtimes remain available when the visitor is in the Farmington area."
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"Added location-aware Box Office news for {len(locations)} U.S. states/territories.")


if __name__ == "__main__":
    main()
