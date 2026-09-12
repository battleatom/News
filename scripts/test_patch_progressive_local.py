from pathlib import Path

p = Path('assets/location-content-v25.js')
s = p.read_text(encoding='utf-8')

required = (
    '__locationContentV34',
    'data/us_news_markets.json',
    'Nearest active news market',
    'LOCAL_MIN_STORIES',
)
missing = [token for token in required if token not in s]
if missing:
    raise SystemExit('Baked location controller is missing: ' + ', '.join(missing))

print('V34 nationwide market routing is already baked into the branch; no runtime patch required.')
