from __future__ import annotations
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

UA="Mozilla/5.0 Underreported-V6/1.0"
TIMEOUT=18


def _json(url:str)->dict:
    request=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=TIMEOUT) as response:
        return json.load(response)


def _date_key(dt:datetime)->str:
    return dt.strftime("%Y%m%d")


def _watch_url(event:dict)->str:
    for link in event.get("links") or []:
        rel=[str(x).lower() for x in (link.get("rel") or [])]
        if any("watch" in x for x in rel) and link.get("href"):
            return str(link["href"])
    return ""


def _collect_plays(event_id:str)->list[dict]:
    try:
        summary=_json("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event="+urllib.parse.quote(event_id))
    except Exception:
        return []
    plays=summary.get("plays") or []
    if not plays:
        current=((summary.get("drives") or {}).get("current") or {}).get("plays") or []
        previous=(summary.get("drives") or {}).get("previous") or []
        plays=[*current,*[play for drive in previous for play in (drive.get("plays") or [])]]
    if not plays:
        plays=summary.get("scoringPlays") or []
    rows=[]
    for play in plays[-8:]:
        text=play.get("text") or play.get("shortText") or ""
        if not text:
            continue
        clock=play.get("clock") or {}
        period=play.get("period") or {}
        rows.append({
            "clock":clock.get("displayValue") if isinstance(clock,dict) else str(clock or ""),
            "period":period.get("number") if isinstance(period,dict) else period or "",
            "text":text,
        })
    return rows[-4:]


def collect_nfl()->tuple[list[dict],str]:
    """Canonical V6 NFL scoreboard: yesterday through the next seven days, with live details."""
    now=datetime.now(timezone.utc)
    start=now-timedelta(days=1)
    end=now+timedelta(days=7)
    url=("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
         f"?limit=64&dates={_date_key(start)}-{_date_key(end)}")
    try:
        payload=_json(url)
        rows=[]
        for event in payload.get("events") or []:
            competition=(event.get("competitions") or [{}])[0]
            teams=[]
            for comp in competition.get("competitors") or []:
                team=comp.get("team") or {}
                teams.append({
                    "name":team.get("displayName") or team.get("shortDisplayName") or "",
                    "abbr":team.get("abbreviation") or "",
                    "score":comp.get("score") or "",
                    "homeAway":comp.get("homeAway") or "",
                    "logo":team.get("logo") or "",
                    "color":team.get("color") or "",
                    "alternateColor":team.get("alternateColor") or "",
                })
            status_type=((event.get("status") or {}).get("type") or {})
            state=status_type.get("state") or ""
            event_id=str(event.get("id") or "")
            broadcasts=list(dict.fromkeys(name for group in (competition.get("broadcasts") or []) for name in (group.get("names") or []) if name))
            rows.append({
                "id":event_id,
                "name":event.get("name") or "",
                "shortName":event.get("shortName") or "",
                "date":event.get("date") or "",
                "status":status_type.get("description") or "",
                "detail":status_type.get("shortDetail") or status_type.get("detail") or "",
                "state":state,
                "teams":teams,
                "broadcasts":broadcasts,
                "watchUrl":_watch_url(event),
                "venue":((competition.get("venue") or {}).get("fullName") or ""),
                "plays":_collect_plays(event_id) if state=="in" and event_id else [],
            })
        return rows,""
    except Exception as exc:
        return [],f"{type(exc).__name__}: {exc}"
