from __future__ import annotations

import difflib
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
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
        heading_html = m.group(1)
        heading = clean(heading_html)
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
        href = re.search(r'href=["\']([^"\']+)["\']', heading_html, re.I)
        movie_url = urllib.parse.urljoin(SHOWTIMES_URL, html.unescape(href.group(1))) if href else ""
        theaters.append({
            "title": heading.replace(" Watch Trailer", "").strip(),
            "theater": current_theater,
            "rating": info.group(1) if info else "",
            "genres": info.group(2).strip() if info else "",
            "runtime": runtime.group(1) if runtime else "",
            "showtimes": list(dict.fromkeys(times)),
            "movieUrl": movie_url,
        })
    merged = {}
    for row in theaters:
        key = (row["theater"], row["title"])
        if key not in merged:
            merged[key] = row
        else:
            merged[key]["showtimes"] = list(dict.fromkeys(merged[key]["showtimes"] + row["showtimes"]))
            if not merged[key].get("movieUrl") and row.get("movieUrl"):
                merged[key]["movieUrl"] = row["movieUrl"]
    return list(merged.values())


def parse_releases(page: str) -> list[dict]:
    month_re = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"

    class ScheduleParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows: list[tuple[str, list[str]]] = []
            self.row: list[str] = []
            self.cell: list[str] | None = None
            self.heading: list[str] | None = None
            self.current_month = ""

        def handle_starttag(self, tag, attrs):
            if tag == "tr":
                self.row = []
            elif tag in ("td", "th"):
                self.cell = []
            elif tag in ("h1", "h2", "h3"):
                self.heading = []

        def handle_data(self, data):
            if self.cell is not None:
                self.cell.append(data)
            if self.heading is not None:
                self.heading.append(data)

        def handle_endtag(self, tag):
            if tag in ("td", "th") and self.cell is not None:
                self.row.append(clean(" ".join(self.cell)))
                self.cell = None
            elif tag == "tr" and self.row:
                self.rows.append((self.current_month, list(self.row)))
            elif tag in ("h1", "h2", "h3") and self.heading is not None:
                heading = clean(" ".join(self.heading))
                m = re.search(fr"\b({month_re})\s+{RELEASE_YEAR}\b", heading, re.I)
                if m:
                    self.current_month = m.group(1).title()
                self.heading = None

    parser = ScheduleParser()
    parser.feed(page)
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    last_date: date | None = None

    for month_hint, row in parser.rows:
        if not row:
            continue
        first = clean(row[0])
        if first.lower() in {"release date", "date", "movie"}:
            continue

        date_match = re.search(fr"\b({month_re})\s+(\d{{1,2}})(?:,?\s+({RELEASE_YEAR}))?\b", first, re.I)
        if date_match:
            month_name = date_match.group(1).title()
            day_num = int(date_match.group(2))
            try:
                last_date = datetime.strptime(f"{month_name} {day_num} {RELEASE_YEAR}", "%B %d %Y").date()
            except ValueError:
                last_date = None
            title_idx = 1
        elif re.fullmatch(r"\d{1,2}", first) and month_hint:
            try:
                last_date = datetime.strptime(f"{month_hint} {int(first)} {RELEASE_YEAR}", "%B %d %Y").date()
            except ValueError:
                last_date = None
            title_idx = 1
        elif not first and last_date is not None:
            title_idx = 1
        elif last_date is not None and month_hint and first:
            # The Numbers sometimes omits the repeated date cell on subsequent
            # releases for the same day, leaving the movie title as the first cell.
            title_idx = 0
        else:
            continue

        if last_date is None or title_idx >= len(row):
            continue
        title = clean(row[title_idx])
        title = re.sub(r"\s*\([^)]*(?:Wide|Limited|IMAX|re-release|Special Engagement|Event)[^)]*\)\s*$", "", title, flags=re.I).strip()
        if not title or title.lower() in {"movie", "release date", "distributor", "domestic box office to date"}:
            continue
        key = (title_key(title), last_date.isoformat())
        if not key[0] or key in seen:
            continue
        seen.add(key)
        out.append({"title": title, "releaseDate": last_date.isoformat()})

    return out


def parse_availability_dates(page: str) -> list[date]:
    today = datetime.now(timezone.utc).date()
    found: set[date] = set()

    for y, m, d in re.findall(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", page):
        try:
            found.add(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    for m, d, y in re.findall(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", clean(page)):
        try:
            found.add(date(int(y), int(m), int(d)))
        except ValueError:
            pass

    month_re = r"January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    for mon, day_num, year in re.findall(fr"\b({month_re})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b", clean(page), re.I):
        try:
            parsed = datetime.strptime(f"{mon} {day_num} {year}", "%b %d %Y").date() if len(mon) <= 3 else datetime.strptime(f"{mon} {day_num} {year}", "%B %d %Y").date()
            found.add(parsed)
        except ValueError:
            pass

    return sorted(d for d in found if d >= today)


def google_news(title: str) -> list[dict]:
    q = urllib.parse.quote(f'"{title}" movie when:30d')
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        root = ET.fromstring(fetch(url))
    except Exception:
        return []
    out = []
    for item in root.findall(".//item"):
        t = clean(item.findtext("title"))
        link = item.findtext("link") or ""
        if not t or not link:
            continue
        source = item.find("source")
        out.append({
            "title": t,
            "description": clean(item.findtext("description")),
            "link": link,
            "source": clean(source.text if source is not None else ""),
            "pubDate": clean(item.findtext("pubDate")),
        })
        if len(out) >= MAX_NEWS:
            break
    return out


def summary_is_movie(title: str, data: dict, extract: str) -> bool:
    if not extract or data.get("type", "").endswith("disambiguation"):
        return False
    description = clean(data.get("description", "")).lower()
    combined = f" {description} {extract[:280].lower()} "
    film_signal = any(term in combined for term in (" film ", " movie ", " motion picture ", " directed by ", " screenplay ", " starring ", " documentary ", " animated "))
    if not film_signal:
        return False
    meaningful = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2]
    return not meaningful or any(w in combined for w in meaningful)


def wikipedia_summary(title: str) -> str:
    candidates = [f"{title} (film)", f"{title} ({RELEASE_YEAR} film)", title]
    for candidate in candidates:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(candidate.replace(" ", "_"))
        try:
            data = json.loads(fetch(url))
            extract = clean(data.get("extract", ""))
            if summary_is_movie(title, data, extract):
                return extract
        except Exception:
            continue
    return ""


def enrich(title: str, base: dict) -> dict:
    item = dict(base)
    item["description"] = wikipedia_summary(title)
    item["news"] = google_news(title)
    return item


def main() -> None:
    try:
        local_rows = parse_showtimes(fetch(SHOWTIMES_URL))
    except Exception as exc:
        print(f"Local showtimes unavailable: {exc}")
        local_rows = []

    local: dict[str, dict] = {}
    for row in local_rows:
        movie = local.setdefault(row["title"], {
            "title": row["title"],
            "rating": row["rating"],
            "genres": row["genres"],
            "runtime": row["runtime"],
            "movieUrl": row.get("movieUrl", ""),
            "theaters": [],
        })
        if not movie.get("movieUrl") and row.get("movieUrl"):
            movie["movieUrl"] = row["movieUrl"]
        movie["theaters"].append({"name": row["theater"], "showtimes": row["showtimes"]})

    try:
        releases = parse_releases(fetch(RELEASE_URL))
    except Exception as exc:
        print(f"Release schedule unavailable: {exc}")
        releases = []

    release_by_key = {title_key(r["title"]): r["releaseDate"] for r in releases if title_key(r.get("title", ""))}
    release_keys = list(release_by_key)

    def release_for(title: str) -> str:
        key = title_key(title)
        if key in release_by_key:
            return release_by_key[key]
        if not key:
            return ""
        best_key = ""
        best_score = 0.0
        for candidate in release_keys:
            score = difflib.SequenceMatcher(None, key, candidate).ratio()
            if score > best_score:
                best_key, best_score = candidate, score
        return release_by_key.get(best_key, "") if best_score >= 0.90 else ""

    today_obj = datetime.now(timezone.utc).date()
    today = today_obj.isoformat()

    # Pull each local movie's advertised future dates. We only call a movie
    # "leaving soon" when its confirmed local schedule ends before the furthest
    # schedule horizon seen for other Farmington movies; this avoids guessing a
    # theatrical end date from age alone.
    availability: dict[str, list[date]] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {}
        for title, movie in local.items():
            url = movie.get("movieUrl") or ""
            if url:
                futures[ex.submit(fetch, url)] = title
        for fut in as_completed(futures):
            title = futures[fut]
            try:
                availability[title] = parse_availability_dates(fut.result())
            except Exception as exc:
                availability[title] = []
                print(f"Showtime horizon unavailable for {title}: {exc}")

    confirmed_last = {title: max(days) for title, days in availability.items() if days}
    global_horizon = max(confirmed_last.values()) if confirmed_last else None

    local_titles = list(local.keys())
    local_keys = {title_key(t) for t in local_titles}
    local_titles.sort(key=lambda t: (release_for(t), t.lower()), reverse=True)

    upcoming = [r for r in releases if r["releaseDate"] > today and title_key(r["title"]) not in local_keys]
    upcoming.sort(key=lambda r: (r["releaseDate"], r["title"].lower()))
    upcoming = upcoming[:MAX_UPCOMING]

    all_titles = list(dict.fromkeys(local_titles + [r["title"] for r in upcoming]))
    upcoming_keys = {title_key(r["title"]) for r in upcoming}
    bases = []
    for title in all_titles:
        key = title_key(title)
        release_date = release_for(title)
        in_theaters = title in local
        status = "In theaters" if in_theaters else "Upcoming"
        last_confirmed = confirmed_last.get(title)
        leaving_soon = bool(
            in_theaters
            and last_confirmed
            and global_horizon
            and last_confirmed < global_horizon
            and 0 <= (last_confirmed - today_obj).days <= 7
        )
        bases.append((title, {
            "title": title,
            "status": status,
            "description": "",
            "rating": local.get(title, {}).get("rating", ""),
            "genres": local.get(title, {}).get("genres", ""),
            "runtime": local.get(title, {}).get("runtime", ""),
            "theaters": local.get(title, {}).get("theaters", []),
            "releaseDate": release_date,
            "confirmedThrough": last_confirmed.isoformat() if last_confirmed else "",
            "leavingDate": last_confirmed.isoformat() if leaving_soon and last_confirmed else "",
            "leavingSoon": leaving_soon,
            "isUpcoming": key in upcoming_keys,
            "news": [],
        }))

    movies = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(enrich, title, base): title for title, base in bases}
        for fut in as_completed(futures):
            try:
                movies.append(fut.result())
            except Exception as exc:
                print(f"Movie enrichment failed for {futures[fut]}: {exc}")

    order = {title: i for i, (title, _) in enumerate(bases)}
    movies.sort(key=lambda x: order.get(x["title"], 999))
    OUT.write_text(json.dumps({
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source": SHOWTIMES_URL,
        "releaseSource": RELEASE_URL,
        "localCity": "Farmington, NM",
        "scheduleHorizon": global_horizon.isoformat() if global_horizon else "",
        "movies": movies,
    }, ensure_ascii=False), encoding="utf-8")

    with_release = sum(1 for m in movies if m.get("releaseDate"))
    with_confirmed = sum(1 for m in movies if m.get("confirmedThrough"))
    leaving = sum(1 for m in movies if m.get("leavingSoon"))
    print(
        f"Box Office enrichment: {len(movies)} movies, {len(local)} local titles, "
        f"{len(upcoming)} upcoming releases, {with_release} release dates matched, "
        f"{with_confirmed} local schedule horizons, {leaving} leaving-soon flags."
    )


if __name__ == "__main__":
    main()
