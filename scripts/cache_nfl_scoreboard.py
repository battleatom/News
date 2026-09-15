from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32'
OUT = Path('nfl-scoreboard.json')

req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 NewsApp/5.3.1'})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    events = data.get('events') or []
    if not isinstance(events, list) or not events:
        raise RuntimeError('ESPN scoreboard returned no events')
    payload = {'generatedAt': datetime.now(timezone.utc).isoformat(), 'source': 'ESPN', 'events': events}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Cached {len(events)} NFL scoreboard events.')
except Exception as exc:
    if OUT.exists():
        print(f'NFL live refresh failed; preserving previous cache: {exc}')
    else:
        raise
