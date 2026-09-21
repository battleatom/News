from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ESPN_URL = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64'
NFLVERSE_URL = 'https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv'
OUT = Path('assets/nfl-scoreboard.json')

TEAM_NAMES = {
    'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills',
    'CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns',
    'DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers',
    'HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','JAC':'Jacksonville Jaguars',
    'KC':'Kansas City Chiefs','LA':'Los Angeles Rams','LAR':'Los Angeles Rams','LAC':'Los Angeles Chargers',
    'LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots',
    'NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles',
    'PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers',
    'TEN':'Tennessee Titans','WAS':'Washington Commanders','WSH':'Washington Commanders',
}
ESPN_ABBR = {'JAX':'JAX','JAC':'JAX','LA':'LAR','LAR':'LAR','WSH':'WSH','WAS':'WSH'}


def request_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36',
        'Accept': 'application/json,text/plain,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.espn.com/',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_espn() -> dict:
    data = request_json(ESPN_URL)
    events = data.get('events') or []
    if not isinstance(events, list) or not events:
        raise RuntimeError('ESPN scoreboard returned no events')
    return {'generatedAt': datetime.now(timezone.utc).isoformat(), 'source': 'ESPN', 'events': events}


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'NewsApp-NFL-Cache/5.3.1', 'Accept': 'text/csv,*/*'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8-sig')


def team_obj(abbr: str) -> dict:
    abbr = (abbr or '').strip().upper()
    espn = ESPN_ABBR.get(abbr, abbr)
    full = TEAM_NAMES.get(abbr, abbr or 'NFL Team')
    return {
        'displayName': full,
        'shortDisplayName': full,
        'name': full.split()[-1],
        'abbreviation': espn,
        'logo': f'https://a.espncdn.com/i/teamlogos/nfl/500/{espn.lower()}.png',
    }


def kickoff_iso(gameday: str, gametime: str) -> str:
    # nflverse schedule times are Eastern. Convert to UTC for browser-local rendering.
    raw = f'{gameday} {gametime or "12:00"}'
    local = datetime.strptime(raw, '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo('America/New_York'))
    return local.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def score_value(v: str) -> str:
    v = (v or '').strip()
    if not v or v.upper() in {'NA','NAN'}:
        return ''
    try:
        return str(int(float(v)))
    except ValueError:
        return v


def fetch_nflverse() -> dict:
    rows = list(csv.DictReader(io.StringIO(fetch_text(NFLVERSE_URL))))
    now = datetime.now(timezone.utc)
    lo, hi = now - timedelta(days=2), now + timedelta(days=16)
    events = []
    for row in rows:
        if str(row.get('season') or '') != str(now.year):
            continue
        if (row.get('game_type') or '').strip().upper() == 'PRE':
            continue
        try:
            date = kickoff_iso((row.get('gameday') or '').strip(), (row.get('gametime') or '').strip())
            kickoff = datetime.fromisoformat(date.replace('Z', '+00:00'))
        except Exception:
            continue
        if not (lo <= kickoff <= hi):
            continue
        away, home = (row.get('away_team') or '').strip(), (row.get('home_team') or '').strip()
        away_score, home_score = score_value(row.get('away_score') or ''), score_value(row.get('home_score') or '')
        final = bool(away_score and home_score)
        state = 'post' if final else 'pre'
        detail = 'Final' if final else 'Scheduled'
        events.append({
            'id': (row.get('game_id') or row.get('alt_game_id') or f'{date}-{away}-{home}').strip(),
            'date': date,
            'name': f'{TEAM_NAMES.get(away, away)} at {TEAM_NAMES.get(home, home)}',
            'status': {'type': {'state': state, 'shortDetail': detail, 'detail': detail}},
            'competitions': [{
                'competitors': [
                    {'homeAway': 'away', 'score': away_score, 'team': team_obj(away)},
                    {'homeAway': 'home', 'score': home_score, 'team': team_obj(home)},
                ],
                'broadcasts': [],
            }],
            'links': [],
        })
    events.sort(key=lambda e: e['date'])
    if not events:
        raise RuntimeError('nflverse schedule returned no current/upcoming events')
    return {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'source': 'nflverse schedule backup',
        'liveScores': False,
        'events': events,
    }


def event_key(ev: dict) -> str:
    comp = (ev.get('competitions') or [{}])[0]
    teams = comp.get('competitors') or []
    away = next((t for t in teams if t.get('homeAway') == 'away'), {})
    home = next((t for t in teams if t.get('homeAway') == 'home'), {})
    aa = ((away.get('team') or {}).get('abbreviation') or '').replace('LAR','LA').replace('WSH','WAS').replace('JAX','JAC')
    ha = ((home.get('team') or {}).get('abbreviation') or '').replace('LAR','LA').replace('WSH','WAS').replace('JAX','JAC')
    try:
        day = datetime.fromisoformat(str(ev.get('date') or '').replace('Z', '+00:00')).date().isoformat()
    except Exception:
        day = str(ev.get('date') or '')[:10]
    return f'{day}|{aa}|{ha}'


def main() -> None:
    errors = []
    espn = None
    schedule = None
    try:
        espn = fetch_espn()
        print(f"Fetched {len(espn['events'])} live/current NFL events from ESPN.")
    except Exception as exc:
        errors.append(f'ESPN: {exc}')
        print(f'ESPN NFL live scoreboard unavailable: {exc}')

    try:
        schedule = fetch_nflverse()
        print(f"Fetched {len(schedule['events'])} NFL schedule events from nflverse.")
    except Exception as exc:
        errors.append(f'nflverse: {exc}')
        print(f'nflverse NFL schedule unavailable: {exc}')

    # Always use the wider schedule as the base, then let ESPN replace matching
    # games with fresher live/final status and scores. This prevents ESPN's
    # narrow scoreboard response from collapsing the UI to only today's game.
    merged = {}
    for ev in (schedule or {}).get('events', []):
        merged[event_key(ev)] = ev
    for ev in (espn or {}).get('events', []):
        merged[event_key(ev)] = ev

    if merged:
        payload = {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'source': 'ESPN live + nflverse 16-day schedule',
            'liveScores': bool(espn),
            'events': sorted(merged.values(), key=lambda e: e.get('date') or ''),
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
        print(f"Cached {len(payload['events'])} merged NFL events.")
        return
    if OUT.exists():
        print('NFL refresh sources failed; preserving previous cache: ' + ' | '.join(errors))
        return
    raise RuntimeError('NFL cache unavailable from all sources: ' + ' | '.join(errors))


if __name__ == '__main__':
    main()
