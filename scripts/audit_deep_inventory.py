#!/usr/bin/env python3
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / 'News'
REPORT = ROOT / 'deep-inventory-report.json'
ACTIVE = 50
RESERVE = 25
TARGET = ACTIVE + RESERVE

HIGH_VOLUME = (
    'top','nfl','underreported','world','us','presidential','federal','nm',
    'technology','gaming','military','entertainment'
)
SPECIAL = {'legislation': 30, 'x': 10}

root = ET.parse(FEED).getroot()
counts = Counter((i.findtext('category') or '').strip() for i in root.findall('.//item'))
rows = {}
failures = []
for category in HIGH_VOLUME:
    total = counts.get(category, 0)
    active = min(ACTIVE, total)
    reserve = min(RESERVE, max(0, total - ACTIVE))
    rows[category] = {
        'total': total,
        'activeCapacity': active,
        'reserveCapacity': reserve,
        'target': TARGET,
        'meetsActiveFloor': total >= ACTIVE,
        'meetsFullTarget': total >= TARGET,
    }
    if total < ACTIVE:
        failures.append(f'{category}: {total} < active floor {ACTIVE}')

for category, expected in SPECIAL.items():
    total = counts.get(category, 0)
    rows[category] = {'total': total, 'expected': expected}
    if category == 'x' and total != expected:
        failures.append(f'x: {total} != fixed {expected}')
    elif category == 'legislation' and total < expected:
        failures.append(f'legislation: {total} < {expected}')

report = {
    'policy': {
        'active': ACTIVE,
        'reserve': RESERVE,
        'targetInventory': TARGET,
        'legislationTarget': 30,
        'xFixed': 10,
        'boxOffice': 'excluded/untouched',
    },
    'categories': rows,
    'failures': failures,
}
REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
if failures:
    raise SystemExit('Deep inventory active-floor failures: ' + '; '.join(failures))
