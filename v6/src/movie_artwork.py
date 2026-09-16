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


def _json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def _similarity(left: str, right: str) -> float:
    a, b = _key(left), _key(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


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
    total = len(movies)
    filled = 0
    tmdb_filled = 0
    wiki_filled = 0
    for movie in movies:
        if movie.get("poster"):
            movie.setdefault("artworkSource", movie.get("metadataSource") or "existing")
            continue
        title = str(movie.get("title") or "").strip()
        if not title:
            continue
        release_date = str(movie.get("releaseDate") or "")
        result = _tmdb(title, release_date)
        if not result.get("poster"):
            result = _wikipedia(title, release_date)
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
        if movie["artworkSource"] == "TMDB":
            tmdb_filled += 1
        elif movie["artworkSource"] == "Wikipedia":
            wiki_filled += 1
    poster_count = sum(bool(movie.get("poster")) for movie in movies)
    return {
        "movieCount": total,
        "posterCount": poster_count,
        "missingPosterCount": max(0, total - poster_count),
        "posterCoverage": round((poster_count / total), 4) if total else 0.0,
        "fallbackFilled": filled,
        "tmdbFallbackFilled": tmdb_filled,
        "wikipediaFallbackFilled": wiki_filled,
        "tmdbConfigured": bool(TMDB_API_KEY),
    }
