from __future__ import annotations
import csv
import io
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UA="Mozilla/5.0 Underreported-V6/1.0"
TIMEOUT=20
ESPN_URL="https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64"
NFLVERSE_URL="https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
TEAM_NAMES={
    "ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers","HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars","JAC":"Jacksonville Jaguars","KC":"Kansas City Chiefs","LA":"Los Angeles Rams","LAR":"Los Angeles Rams","LAC":"Los Angeles Chargers","LV":"Las Vegas Raiders","MIA":"Miami Dolphins","MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SEA":"Seattle Seahawks","SF":"San Francisco 49ers","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders","WSH":"Washington Commanders",
}
ESPN_ABBR={"JAC":"JAX","JAX":"JAX","LA":"LAR","LAR":"LAR","WAS":"WSH","WSH":"WSH"}


def _request(url:str,accept:str)->bytes:
    request=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":accept,"Referer":"https://www.espn.com/"})
    with urllib.request.urlopen(request,timeout=TIMEOUT) as response:
        return response.read()


def _json(url:str)->dict:
    return json.loads(_request(url,"application/json,text/plain,*/*"))


def _text(url:str)->str:
    return _request(url,"text/csv,*/*").decode("utf-8-sig","replace")


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
        rows.append({"clock":clock.get("displayValue") if isinstance(clock,dict) else str(clock or ""),"period":period.get("number") if isinstance(period,dict) else period or "","text":text})
    return rows[-4:]


def _normalized_espn(event:dict)->dict:
    competition=(event.get("competitions") or [{}])[0]
    teams=[]
    for comp in competition.get("competitors") or []:
        team=comp.get("team") or {}
        teams.append({"name":team.get("displayName") or team.get("shortDisplayName") or "","abbr":team.get("abbreviation") or "","score":comp.get("score") or "","homeAway":comp.get("homeAway") or "","logo":team.get("logo") or "","color":team.get("color") or "","alternateColor":team.get("alternateColor") or ""})
    status_type=((event.get("status") or {}).get("type") or {})
    state=status_type.get("state") or ""
    event_id=str(event.get("id") or "")
    broadcasts=list(dict.fromkeys(name for group in (competition.get("broadcasts") or []) for name in (group.get("names") or []) if name))
    return {"id":event_id,"name":event.get("name") or "","shortName":event.get("shortName") or "","date":event.get("date") or "","status":status_type.get("description") or "","detail":status_type.get("shortDetail") or status_type.get("detail") or "","state":state,"teams":teams,"broadcasts":broadcasts,"watchUrl":_watch_url(event),"venue":((competition.get("venue") or {}).get("fullName") or ""),"plays":_collect_plays(event_id) if state=="in" and event_id else []}


def _kickoff_iso(gameday:str,gametime:str)->str:
    local=datetime.strptime(f"{gameday} {gametime or '12:00'}","%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc).isoformat().replace("+00:00","Z")


def _score(value:str)->str:
    value=(value or "").strip()
    if not value or value.upper() in {"NA","NAN"}:
        return ""
    try:return str(int(float(value)))
    except ValueError:return value


def _team(abbr:str,home_away:str,score:str)->dict:
    raw=(abbr or "").strip().upper();espn=ESPN_ABBR.get(raw,raw);name=TEAM_NAMES.get(raw,raw or "NFL Team")
    return {"name":name,"abbr":espn,"score":score,"homeAway":home_away,"logo":f"https://a.espncdn.com/i/teamlogos/nfl/500/{espn.lower()}.png","color":"","alternateColor":""}


def _nflverse_rows(now:datetime)->list[dict]:
    rows=[];lo=now-timedelta(days=2);hi=now+timedelta(days=7)
    for row in csv.DictReader(io.StringIO(_text(NFLVERSE_URL))):
        if str(row.get("season") or "")!=str(now.year) or (row.get("game_type") or "").strip().upper()=="PRE":
            continue
        try:
            date=_kickoff_iso((row.get("gameday") or "").strip(),(row.get("gametime") or "").strip());kickoff=datetime.fromisoformat(date.replace("Z","+00:00"))
        except Exception:
            continue
        if not(lo<=kickoff<=hi):
            continue
        away=(row.get("away_team") or "").strip();home=(row.get("home_team") or "").strip();away_score=_score(row.get("away_score") or "");home_score=_score(row.get("home_score") or "");final=bool(away_score and home_score);state="post" if final else "pre"
        rows.append({"id":str(row.get("game_id") or row.get("alt_game_id") or f"{date}-{away}-{home}"),"name":f"{TEAM_NAMES.get(away,away)} at {TEAM_NAMES.get(home,home)}","shortName":f"{ESPN_ABBR.get(away,away)} @ {ESPN_ABBR.get(home,home)}","date":date,"status":"Final" if final else "Scheduled","detail":"Final" if final else "Scheduled","state":state,"teams":[_team(away,"away",away_score),_team(home,"home",home_score)],"broadcasts":[],"watchUrl":"","venue":"","plays":[]})
    return rows


def _game_key(game:dict)->str:
    teams=game.get("teams") or [];away=next((t for t in teams if t.get("homeAway")=="away"),{});home=next((t for t in teams if t.get("homeAway")=="home"),{});ts=0
    try:ts=round(datetime.fromisoformat(str(game.get("date") or "").replace("Z","+00:00")).timestamp()/600)
    except Exception:pass
    return f"{away.get('abbr','')}|{home.get('abbr','')}|{ts}"


def collect_nfl()->tuple[list[dict],str]:
    """Canonical V6 NFL service: live ESPN details merged with a resilient current schedule window."""
    now=datetime.now(timezone.utc);errors=[];espn=[];schedule=[]
    try:
        espn=[_normalized_espn(event) for event in (_json(ESPN_URL).get("events") or [])]
    except Exception as exc:
        errors.append(f"ESPN: {type(exc).__name__}: {exc}")
    try:
        schedule=_nflverse_rows(now)
    except Exception as exc:
        errors.append(f"nflverse: {type(exc).__name__}: {exc}")
    merged={}
    for game in schedule:
        key=_game_key(game)
        if key:merged[key]=game
    for game in espn:
        key=_game_key(game)
        if key:merged[key]=game
    games=sorted(merged.values(),key=lambda g:g.get("date") or "")
    if games:
        return games,"; ".join(errors)
    return [],"; ".join(errors) or "NFL scoreboard contains no events"
