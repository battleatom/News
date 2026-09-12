#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / 'data' / 'us_news_markets.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
markets = []
for rel in manifest.get('files', []):
    payload = json.loads((manifest_path.parent / rel).read_text(encoding='utf-8'))
    assert payload.get('markets'), f'empty market file: {rel}'
    markets.extend(payload['markets'])

assert len(markets) >= 120, f'expected nationwide market coverage, got {len(markets)}'
ids = [m['id'] for m in markets]
assert len(ids) == len(set(ids)), 'duplicate market IDs'

required_states = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
covered_states = {m['state'] for m in markets}
missing = sorted(required_states - covered_states)
assert not missing, f'missing states/territories: {missing}'

for m in markets:
    assert m.get('city') and m.get('stateName') and m.get('region') and m.get('query'), m
    assert -90 <= float(m['lat']) <= 90 and -180 <= float(m['lon']) <= 180, m
    assert m.get('sources'), f"market has no approved local sources: {m['id']}"

controller = (ROOT / 'assets' / 'location-content-v25.js').read_text(encoding='utf-8')
assert '__locationContentV34' in controller
assert 'data/us_news_markets.json' in controller
assert 'Nearest active news market' in controller
assert 'FOUR_CORNERS_CITIES' not in controller

wrapper = (ROOT / 'scripts' / 'update_news_normalized.py').read_text(encoding='utf-8')
assert 'LOCAL_STORIES_PER_MARKET' in wrapper
assert 'marketId' in wrapper and 'marketCity' in wrapper and 'marketState' in wrapper
assert 'local_story_relevant' in wrapper

print(f'News-market database passed: {len(markets)} markets across all 50 states + DC; routing/collector integration present.')
