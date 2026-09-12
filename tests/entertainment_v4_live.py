#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update_news_v4 as v4

items=[]
for query in v4.core.QUERIES['entertainment']:
    try:
        batch=v4.core.parse_items(v4.core.fetch(query),'entertainment')
        items.extend(batch)
        print(f'{query}: {len(batch)} accepted')
    except Exception as exc:
        print(f'query failed: {query}: {exc}')

selected=v4.select_entertainment(items,limit=15)
print(f'LIVE ENTERTAINMENT: {len(selected)} selected')
for i,x in enumerate(selected[:15],1):
    print(f"{i}. [{x.get('entertainmentLabel')}/{x.get('entertainmentSafety')}] {x.get('title')} - {x.get('source')}")
if len(selected)<5:
    raise SystemExit(f'Expected at least 5 verified live Entertainment stories, got {len(selected)}')
if any(x.get('entertainmentSafety') not in {'clean','dirty'} for x in selected):
    raise SystemExit('Live Entertainment story missing Clean/Dirty classification')
if any(not x.get('entertainmentLabel') for x in selected):
    raise SystemExit('Live Entertainment story missing importance label')
scores=[int(x.get('entertainmentScore') or 0) for x in selected]
if scores != sorted(scores,reverse=True):
    raise SystemExit(f'Importance hierarchy is not descending: {scores}')
print('Live V4 Entertainment source check passed: importance hierarchy and Clean/Dirty metadata verified.')
