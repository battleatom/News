from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = "Underreported-V6/1.0 (+https://battleatom.github.io/)"
TIMEOUT = 15

def fetch_json(url: str) -> dict:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as response: return json.load(response)

def collect_nfl() -> tuple[list[dict], str]:
    url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        payload=fetch_json(url);rows=[]
        for event in payload.get("events",[]):
            competition=(event.get("competitions") or [{}])[0];competitors=competition.get("competitors") or [];teams=[]
            for comp in competitors:
                team=comp.get("team") or {}
                teams.append({"name":team.get("displayName") or team.get("shortDisplayName") or "","abbr":team.get("abbreviation") or "","score":comp.get("score") or "","homeAway":comp.get("homeAway") or ""})
            rows.append({"id":event.get("id") or "","name":event.get("name") or "","shortName":event.get("shortName") or "","date":event.get("date") or "","status":((event.get("status") or {}).get("type") or {}).get("description") or "","detail":((event.get("status") or {}).get("type") or {}).get("detail") or "","teams":teams,"broadcasts":[name for group in competition.get("broadcasts",[]) for name in group.get("names",[])]})
        return rows,""
    except Exception as exc: return [],f"{type(exc).__name__}: {exc}"

def collect_boxoffice() -> tuple[list[dict], str]:
    key=os.environ.get("TMDB_API_KEY","").strip()
    if not key: return [],"TMDB_API_KEY is not configured; Box Office is disabled in this V6 test build."
    try:
        playing=fetch_json("https://api.themoviedb.org/3/movie/now_playing?"+urllib.parse.urlencode({"api_key":key,"language":"en-US","region":"US","page":1}))
        upcoming=fetch_json("https://api.themoviedb.org/3/movie/upcoming?"+urllib.parse.urlencode({"api_key":key,"language":"en-US","region":"US","page":1}))
        rows=[];seen=set()
        for status,payload in (("playing",playing),("upcoming",upcoming)):
            for movie in payload.get("results",[]):
                mid=str(movie.get("id") or "")
                if not mid or mid in seen: continue
                seen.add(mid)
                rows.append({"id":mid,"title":movie.get("title") or "","releaseDate":movie.get("release_date") or "","overview":movie.get("overview") or "","poster":("https://image.tmdb.org/t/p/w500"+movie["poster_path"]) if movie.get("poster_path") else "","status":status,"voteAverage":movie.get("vote_average") or 0})
        rows.sort(key=lambda m:((0 if m["status"]=="playing" else 1),m.get("releaseDate") or "9999"));return rows,""
    except Exception as exc: return [],f"{type(exc).__name__}: {exc}"
