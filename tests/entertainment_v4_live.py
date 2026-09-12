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
    print(f"{i}. [{x.get('entertainmentTier')}] {x.get('title')} - {x.get('source')}")
if len(selected)<5:
    raise SystemExit(f'Expected at least 5 verified live Entertainment stories, got {len(selected)}')
if any(x.get('entertainmentTier')!='newest' for x in selected[:5]):
    raise SystemExit('Top five live Entertainment stories are not marked newest')
print('Live V4 Entertainment source check passed.')
