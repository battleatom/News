from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

OUT = Path("boxoffice.json")
SHOWTIMES_URL = "https://www.showtimes.com/movie-times/farmington-nm/"
RELEASE_URL = "https://www.the-numbers.com/movies/release-schedule/2026"
MAX_NEWS = 3


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Underreported/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def clean(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_showtimes(page: str) -> list[dict]:
    headings = list(re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2[^>]*>|</main>|</body>)", page, re.I | re.S))
    theaters = []
    current_theater = ""
    for m in headings:
        heading = clean(m.group(1))
        block = clean(m.group(2))
        if heading.lower().startswith("allen theatres"):
            current_theater = heading
            continue
        if not current_theater or not heading or len(heading) > 120:
            continue
        info = re.search(r"\b(G|PG|PG-13|R|NC-17|NR)\b\s*[·|]\s*([^·|]{3,100})", block)
        runtime = re.search(r"\b(\d+h\s*\d+m|\d+h|\d+m)\b", block)
        times = re.findall(r"\b(?:[1-9]|1[0-2]):[0-5]\d\s*(?:am|pm)\b", block, re.I)
        if not times:
            continue
        theaters.append({
            "title": heading.replace(" Watch Trailer", "").strip(),
            "theater": current_theater,
            "rating": info.group(1) if info else "",
            "genres": info.group(2).strip() if info else "",
            "runtime": runtime.group(1) if runtime else "",
            "showtimes": list(dict.fromkeys(times)),
        })
    merged = {}
    for row in theaters:
        key = (row["theater"], row["title"])
        if key not in merged:
            merged[key] = row
        else:
            merged[key]["showtimes"] = list(dict.fromkeys(merged[key]["showtimes"] + row["showtimes"]))
    return list(merged.values())


def parse_releases(page: str) -> list[dict]:
    class TableParser(HTMLParser):
        def __init__(self):
            super().__init__(); self.rows=[]; self.row=[]; self.cell=None
        def handle_starttag(self, tag, attrs):
            if tag == "tr": self.row=[]
            elif tag in ("td","th"): self.cell=[]
        def handle_data(self, data):
            if self.cell is not None: self.cell.append(data)
        def handle_endtag(self, tag):
            if tag in ("td","th") and self.cell is not None:
                self.row.append(clean(" ".join(self.cell))); self.cell=None
            elif tag == "tr" and self.row: self.rows.append(self.row)
    p=TableParser(); p.feed(page)
    out=[]; current_month=""
    for row in p.rows:
        if not row: continue
        if re.fullmatch(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) 2026", row[0] or ""):
            current_month=row[0]; continue
        if not current_month or not re.match(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}", row[0] or "") or len(row)<2:
            continue
        title=re.sub(r"\s*\([^)]*\)\s*$", "", row[1]).strip()
        try: dt=datetime.strptime(f"{row[0]} 2026", "%B %d %Y").replace(tzinfo=timezone.utc)
        except Exception: continue
        if title and title.lower() not in {"movie","release date"}:
            out.append({"title":title,"releaseDate":dt.date().isoformat()})
    return out


def google_news(title: str) -> list[dict]:
    q=urllib.parse.quote(f'"{title}" movie when:30d'); url=f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try: root=ET.fromstring(fetch(url))
    except Exception: return []
    out=[]
    for item in root.findall(".//item"):
        t=clean(item.findtext("title")); link=item.findtext("link") or ""
        if not t or not link: continue
        source=item.find("source")
        out.append({"title":t,"description":clean(item.findtext("description")),"link":link,"source":clean(source.text if source is not None else ""),"pubDate":clean(item.findtext("pubDate"))})
        if len(out)>=MAX_NEWS: break
    return out


def wikipedia_summary(title: str) -> str:
    url="https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(title.replace(" ","_"))
    try:
        data=json.loads(fetch(url)); extract=clean(data.get("extract",""))
        if extract and not data.get("type","").endswith("disambiguation"): return extract
    except Exception: pass
    return ""


def enrich(title: str, base: dict) -> dict:
    item=dict(base); item["description"]=wikipedia_summary(title); item["news"]=google_news(title); return item


def main() -> None:
    try: local_rows=parse_showtimes(fetch(SHOWTIMES_URL))
    except Exception as exc: print(f"Local showtimes unavailable: {exc}"); local_rows=[]
    local={}
    for row in local_rows:
        local.setdefault(row["title"], {"title":row["title"],"rating":row["rating"],"genres":row["genres"],"runtime":row["runtime"],"theaters":[]})["theaters"].append({"name":row["theater"],"showtimes":row["showtimes"]})
    try: releases=parse_releases(fetch(RELEASE_URL))
    except Exception as exc: print(f"Release schedule unavailable: {exc}"); releases=[]
    today=datetime.now(timezone.utc).date().isoformat()
    upcoming=[r for r in releases if r["releaseDate"]>=today][:20]
    local_titles=set(local)
    all_titles=list(dict.fromkeys(list(local_titles)+[r["title"] for r in upcoming]))[:25]
    bases=[]
    for title in all_titles:
        bases.append((title,{"title":title,"status":"In theaters" if title in local_titles else "Upcoming","description":"","rating":local.get(title,{}).get("rating",""),"genres":local.get(title,{}).get("genres",""),"runtime":local.get(title,{}).get("runtime",""),"theaters":local.get(title,{}).get("theaters",[]),"releaseDate":next((r["releaseDate"] for r in upcoming if r["title"]==title),""),"news":[]}))
    movies=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures={ex.submit(enrich,title,base):title for title,base in bases}
        for fut in as_completed(futures):
            try: movies.append(fut.result())
            except Exception as exc: print(f"Movie enrichment failed for {futures[fut]}: {exc}")
    order={title:i for i,(title,_) in enumerate(bases)}; movies.sort(key=lambda x:order.get(x["title"],999))
    OUT.write_text(json.dumps({"updatedAt":datetime.now(timezone.utc).isoformat(),"source":SHOWTIMES_URL,"releaseSource":RELEASE_URL,"localCity":"Farmington, NM","movies":movies},ensure_ascii=False),encoding="utf-8")
    print(f"Box Office enrichment: {len(movies)} movies, {len(local)} local titles, {len(upcoming)} upcoming releases.")

if __name__ == "__main__": main()
