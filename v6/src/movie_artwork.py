from __future__ import annotations

import difflib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = "Mozilla/5.0 Underreported-V6/1.0"
TIMEOUT = 15
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
CURRENT_YEAR = datetime.now(timezone.utc).year


def _clean(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean(value).lower().replace("&", " and "))


def _request(url: str, accept: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.8"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def _json(url: str) -> dict:
    return json.loads(_request(url, "application/json").decode("utf-8", "replace"))


def _text(url: str) -> str:
    return _request(url, "text/html,application/xhtml+xml").decode("utf-8", "replace")


def _similarity(left: str, right: str) -> float:
    a, b = _key(left), _key(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _is_schedule_label(title: str) -> bool:
    value = _clean(title).lower()
    if not value:
        return True
    month_names = "january|february|march|april|may|june|july|august|september|october|november|december"
    season_names = "spring|summer|fall|autumn|winter"
    if re.fullmatch(rf"(?:{month_names})\s+20\d{{2}}", value):
        return True
    if re.fullmatch(rf"(?:{season_names})\s+20\d{{2}}", value):
        return True
    if re.fullmatch(r"(?:1st|2nd|3rd|4th)\s+quarter", value):
        return True
    if value in {"time", "date", "title", "movie", "movies", "release date", "release schedule", "tbd", "to be announced"}:
        return True
    return False


def _title_variants(title: str) -> list[str]:
    title = _clean(title)
    variants = [title]
    without_cinema = re.sub(r"\s+in\s+cinemas\s*$", "", title, flags=re.I).strip()
    if without_cinema and without_cinema not in variants:
        variants.append(without_cinema)
    without_suffix = re.sub(r"\s*[:–—-]\s*(?:the\s+)?(?:trilogy\s+)?concert.*$", "", without_cinema, flags=re.I).strip()
    if without_suffix and len(without_suffix) >= 4 and without_suffix not in variants:
        variants.append(without_suffix)
    if ":" in title:
        short = title.split(":", 1)[0].strip()
        if len(short) >= 4 and short not in variants:
            variants.append(short)
    return variants


def _tmdb(title: str, release_date: str = "") -> dict:
    if not TMDB_API_KEY:
        return {}
    target_year = (release_date or "")[:4]
    attempts = [target_year] if target_year.isdigit() else []
    attempts.append("")
    best = None
    best_score = 0.0
    for year in attempts:
        try:
            params = {"api_key": TMDB_API_KEY, "query": title, "include_adult": "false", "language": "en-US"}
            if year:
                params["year"] = year
            payload = _json("https://api.themoviedb.org/3/search/movie?" + urllib.parse.urlencode(params))
            for item in payload.get("results") or []:
                candidate_title = item.get("title") or item.get("original_title") or ""
                score = _similarity(title, candidate_title)
                item_year = str(item.get("release_date") or "")[:4]
                if target_year and item_year == target_year:
                    score += 0.08
                elif target_year and item_year and item_year != target_year:
                    score -= 0.06
                if item.get("poster_path"):
                    score += 0.03
                if score > best_score:
                    best_score, best = score, item
        except Exception:
            continue
    if not best or best_score < 0.82:
        return {}
    poster = best.get("poster_path") or ""
    return {
        "poster": TMDB_IMAGE_BASE + poster if poster else "",
        "overview": _clean(best.get("overview") or ""),
        "voteAverage": best.get("vote_average") or 0,
        "tmdbId": best.get("id") or "",
        "metadataSource": "TMDB",
        "artworkSource": "TMDB" if poster else "",
    }


def _meta(page: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(key)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.I | re.S)
        if match:
            return html.unescape(match.group(1)).strip()
    return ""


def _tmdb_web(title: str, release_date: str = "") -> dict:
    try:
        search_url = "https://www.themoviedb.org/search/movie?" + urllib.parse.urlencode({"query": title, "language": "en-US"})
        search_page = _text(search_url)
    except Exception:
        return {}
    paths = []
    for match in re.finditer(r'href=["\'](/movie/\d+[^"\']*)["\']', search_page, re.I):
        path = html.unescape(match.group(1)).split("?")[0]
        if path not in paths:
            paths.append(path)
        if len(paths) >= 8:
            break
    target_year = (release_date or "")[:4]
    best = {}
    best_score = 0.0
    for path in paths:
        try:
            page = _text(urllib.parse.urljoin("https://www.themoviedb.org", path))
        except Exception:
            continue
        page_title = _meta(page, "og:title") or _clean((re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S) or ["", ""])[1])
        page_title = re.sub(r"\s*[—|-]\s*The Movie Database.*$", "", page_title, flags=re.I).strip()
        score = _similarity(title, re.sub(r"\s*\(\d{4}\)\s*$", "", page_title))
        if target_year and target_year in page:
            score += 0.06
        poster = _meta(page, "og:image") or _meta(page, "twitter:image")
        if poster:
            score += 0.03
        if score > best_score and poster:
            movie_id_match = re.search(r"/movie/(\d+)", path)
            best_score = score
            best = {
                "poster": poster,
                "overview": _meta(page, "og:description"),
                "tmdbId": movie_id_match.group(1) if movie_id_match else "",
                "metadataSource": "TMDB Web",
                "artworkSource": "TMDB Web",
            }
    return best if best_score >= 0.78 else {}


def _showtimes_artwork(movie_url: str) -> dict:
    if not movie_url or "showtimes.com" not in movie_url:
        return {}
    try:
        page = _text(movie_url)
    except Exception:
        return {}
    poster = _meta(page, "og:image") or _meta(page, "twitter:image")
    if not poster:
        image_matches = re.findall(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\'][^>]*>', page, re.I | re.S)
        poster = next((html.unescape(url) for url in image_matches if any(token in url.lower() for token in ("poster", "movie", "film"))), "")
    if not poster:
        return {}
    return {
        "poster": urllib.parse.urljoin(movie_url, poster),
        "overview": _meta(page, "og:description"),
        "metadataSource": "Showtimes.com",
        "artworkSource": "Showtimes.com",
    }


def _wiki_summary(page_title: str) -> dict:
    try:
        payload = _json("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(page_title.replace(" ", "_")))
    except Exception:
        return {}
    extract = _clean(payload.get("extract") or "")
    description = _clean(payload.get("description") or "")
    text = f" {description.lower()} {extract[:400].lower()} "
    if not any(token in text for token in (" film ", " movie ", " motion picture ", " directed by ", " starring ", " documentary ", " animated ")):
        return {}
    poster = ((payload.get("thumbnail") or {}).get("source") or "").strip()
    return {
        "poster": poster,
        "overview": extract,
        "metadataSource": "Wikipedia",
        "artworkSource": "Wikipedia" if poster else "",
        "wikiTitle": payload.get("title") or page_title,
    }


def _wikipedia(title: str, release_date: str = "") -> dict:
    year = (release_date or "")[:4]
    year = year if year.isdigit() else str(CURRENT_YEAR)
    direct_titles = [f"{title} ({year} film)", f"{title} (film)", title]
    for page_title in direct_titles:
        result = _wiki_summary(page_title)
        if result.get("poster"):
            return result
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": f'"{title}" film {year}',
            "srlimit": "8",
            "format": "json",
            "utf8": "1",
            "origin": "*",
        }
        payload = _json("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params))
    except Exception:
        return {}
    candidates = []
    for row in (payload.get("query") or {}).get("search") or []:
        page_title = _clean(row.get("title") or "")
        if not page_title:
            continue
        score = _similarity(title, re.sub(r"\s*\([^)]*\)\s*$", "", page_title))
        if year in page_title:
            score += 0.08
        if "film" in page_title.lower():
            score += 0.05
        candidates.append((score, page_title))
    for _, page_title in sorted(candidates, reverse=True):
        result = _wiki_summary(page_title)
        if result.get("poster"):
            return result
    return {}


def ensure_movie_artwork(movies: list[dict]) -> dict:
    movies[:] = [movie for movie in movies if not _is_schedule_label(str(movie.get("title") or ""))]
    total = len(movies)
    filled = 0
    source_fills: dict[str, int] = {}
    for movie in movies:
        if movie.get("poster"):
            movie.setdefault("artworkSource", movie.get("metadataSource") or "existing")
            continue
        title = str(movie.get("title") or "").strip()
        if not title:
            continue
        release_date = str(movie.get("releaseDate") or "")
        variants = _title_variants(title)
        result = {}
        for candidate in variants:
            result = _tmdb(candidate, release_date)
            if result.get("poster"):
                break
        if not result.get("poster"):
            for candidate in variants:
                result = _tmdb_web(candidate, release_date)
                if result.get("poster"):
                    break
        if not result.get("poster"):
            result = _showtimes_artwork(str(movie.get("movieUrl") or ""))
        if not result.get("poster"):
            for candidate in variants:
                result = _wikipedia(candidate, release_date)
                if result.get("poster"):
                    break
        if not result.get("poster"):
            continue
        movie["poster"] = result["poster"]
        if not movie.get("overview") and result.get("overview"):
            movie["overview"] = result["overview"]
        if not movie.get("tmdbId") and result.get("tmdbId"):
            movie["tmdbId"] = result["tmdbId"]
        if not movie.get("voteAverage") and result.get("voteAverage"):
            movie["voteAverage"] = result["voteAverage"]
        if result.get("metadataSource"):
            movie["metadataSource"] = result["metadataSource"]
        movie["artworkSource"] = result.get("artworkSource") or result.get("metadataSource") or "fallback"
        filled += 1
        source_fills[movie["artworkSource"]] = source_fills.get(movie["artworkSource"], 0) + 1
    poster_count = sum(bool(movie.get("poster")) for movie in movies)
    return {
        "movieCount": total,
        "posterCount": poster_count,
        "missingPosterCount": max(0, total - poster_count),
        "posterCoverage": round((poster_count / total), 4) if total else 0.0,
        "fallbackFilled": filled,
        "fallbackFilledBySource": source_fills,
        "tmdbConfigured": bool(TMDB_API_KEY),
    }
