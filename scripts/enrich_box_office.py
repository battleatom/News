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
RELEASE_YEAR = datetime.now(timezone.utc).year
RELEASE_URL = f"https://www.the-numbers.com/movies/release-schedule/{RELEASE_YEAR}"
MAX_NEWS = 3
MAX_UPCOMING = 20


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Underreported/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def clean(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_key(value: str) -> str:
    value = clean(value).lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", value)


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
    month_re = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    for row in p.rows:
        if not row: continue
        if re.fullmatch(fr"{month_re} {RELEASE_YEAR}", row[0] or ""):
            current_month=row[0]; continue
        if not current_month or not re.match(fr"{month_re} \d{{1,2}}", row[0] or "") or len(row)<2:
            continue
        title=re.sub(r"\s*\([^)]*\)\s*$", "", row[1]).strip()
        try: dt=datetime.strptime(f"{row[0]} {RELEASE_YEAR}", "%B %d %Y").replace(tzinfo=timezone.utc)
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


def summary_is_movie(title: str, data: dict, extract: str) -> bool:
    if not extract or data.get("type","").endswith("disambiguation"):
        return False
    description=clean(data.get("description","")).lower()
    combined=f" {description} {extract[:280].lower()} "
    film_signal=any(term in combined for term in (" film "," movie "," motion picture "," directed by "," screenplay "," starring "," documentary "," animated "))
    if not film_signal:
        return False
    meaningful=[w for w in re.findall(r"[a-z0-9]+",title.lower()) if len(w)>2]
    return not meaningful or any(w in combined for w in meaningful)


def wikipedia_summary(title: str) -> str:
    candidates=[f"{title} (film)", f"{title} ({RELEASE_YEAR} film)", title]
    for candidate in candidates:
        url="https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(candidate.replace(" ","_"))
        try:
            data=json.loads(fetch(url)); extract=clean(data.get("extract",""))
            if summary_is_movie(title,data,extract): return extract
        except Exception:
            continue
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

    release_by_key={title_key(r["title"]):r["releaseDate"] for r in releases if title_key(r.get("title",""))}
    def release_for(title: str) -> str:
        return release_by_key.get(title_key(title), "")

    today=datetime.now(timezone.utc).date().isoformat()
    local_titles=list(local.keys())
    local_keys={title_key(t) for t in local_titles}
    local_titles.sort(key=lambda t:(release_for(t), t.lower()), reverse=True)

    upcoming=[r for r in releases if r["releaseDate"]>today and title_key(r["title"]) not in local_keys]
    upcoming.sort(key=lambda r:(r["releaseDate"], r["title"].lower()))
    upcoming=upcoming[:MAX_UPCOMING]

    all_titles=list(dict.fromkeys(local_titles+[r["title"] for r in upcoming]))
    upcoming_keys={title_key(r["title"]) for r in upcoming}
    bases=[]
    for title in all_titles:
        key=title_key(title)
        release_date=release_for(title)
        in_theaters=title in local
        status="In theaters" if in_theaters else "Upcoming"
        bases.append((title,{
            "title":title,
            "status":status,
            "description":"",
            "rating":local.get(title,{}).get("rating",""),
            "genres":local.get(title,{}).get("genres",""),
            "runtime":local.get(title,{}).get("runtime",""),
            "theaters":local.get(title,{}).get("theaters",[]),
            "releaseDate":release_date,
            "leavingDate":"",
            "leavingSoon":False,
            "isUpcoming":key in upcoming_keys,
            "news":[]
        }))

    movies=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures={ex.submit(enrich,title,base):title for title,base in bases}
        for fut in as_completed(futures):
            try: movies.append(fut.result())
            except Exception as exc: print(f"Movie enrichment failed for {futures[fut]}: {exc}")

    order={title:i for i,(title,_) in enumerate(bases)}
    movies.sort(key=lambda x:order.get(x["title"],999))
    OUT.write_text(json.dumps({
        "updatedAt":datetime.now(timezone.utc).isoformat(),
        "source":SHOWTIMES_URL,
        "releaseSource":RELEASE_URL,
        "localCity":"Farmington, NM",
        "movies":movies
    },ensure_ascii=False),encoding="utf-8")
    with_release=sum(1 for m in movies if m.get("releaseDate"))
    print(f"Box Office enrichment: {len(movies)} movies, {len(local)} local titles, {len(upcoming)} upcoming releases, {with_release} release dates matched.")

if __name__ == "__main__": main()
