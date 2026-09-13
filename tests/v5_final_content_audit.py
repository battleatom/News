#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import enforce_editorial_integrity as editorial
from filter_landing_pages import is_landing_page

NEWS = ROOT / 'News'
OUT = ROOT / 'v5-final-content-audit.json'
EXPECTED_X = [
    'Health','Technology & AI','Celebrities & Public Figures','World',
    'Politics & Government','Entertainment','Sports','Business & Economy',
    'Gaming','Science'
]
REQUIRED = {
    'top','nfl','x','underreported','entertainment','world','us','presidential',
    'federal','legislation','nm','local','region','technology','gaming','military'
}
CONTEXT_CATS = {'entertainment','technology','gaming'}


def text(item, tag):
    return re.sub(r'\s+', ' ', item.findtext(tag) or '').strip()


def norm(value):
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def add(report, kind, message):
    report['failures'].append({'kind': kind, 'message': message})


tree = ET.parse(NEWS)
items = tree.getroot().findall('.//item')
counts = Counter(text(i, 'category').lower() for i in items)
report = {
    'status': 'pass',
    'totalItems': len(items),
    'categoryCounts': dict(sorted(counts.items())),
    'failures': [],
    'warnings': [],
}

if len(items) < 150:
    add(report, 'feed-size', f'Feed unexpectedly small: {len(items)}')
for category in sorted(REQUIRED):
    if counts.get(category, 0) == 0:
        add(report, 'missing-category', f'Required category is empty: {category}')

seen_titles = set()
x_topics = []
why_counts = Counter()
underreported_titles = set()

for n, item in enumerate(items):
    cat = text(item, 'category').lower()
    title = text(item, 'title')
    link = text(item, 'link')
    source = text(item, 'source')
    why = text(item, 'whyMatters')

    missing = [name for name, value in (('title', title), ('link', link), ('source', source), ('category', cat)) if not value]
    if missing:
        add(report, 'malformed-story', f'{cat}#{n} missing {", ".join(missing)}')

    title_key = (cat, norm(title))
    if title_key[1] and title_key in seen_titles:
        add(report, 'duplicate-title', f'{cat}: {title}')
    seen_titles.add(title_key)

    if is_landing_page(item):
        add(report, 'landing-page', f'{cat}: {title}')

    if cat == 'world' and editorial.obvious_domestic_world(item):
        add(report, 'world-leakage', title)

    if cat == 'us':
        action = editorial.us_sports_disposition(item)
        if action:
            add(report, 'us-sports-leakage', f'{action}: {title}')

    if cat == 'x':
        topic = text(item, 'xTopic')
        x_topics.append(topic)
        if not editorial.x_relevant(item, topic):
            add(report, 'x-topic', f'{topic}: {title}')

    if cat == 'underreported':
        nt = norm(title)
        if nt in underreported_titles:
            add(report, 'underreported-duplicate', title)
        underreported_titles.add(nt)

    if cat == 'entertainment':
        safety = text(item, 'entertainmentSafety').lower()
        if safety not in {'clean', 'dirty'}:
            add(report, 'entertainment-metadata', f'Missing/invalid safety tag: {title}')

    if cat in CONTEXT_CATS:
        if not why:
            add(report, 'missing-why', f'{cat}: {title}')
        else:
            why_counts[why] += 1
            if len(why) < 45:
                add(report, 'weak-why', f'{cat}: {title} -> {why}')
            if why.endswith(('...', '…')):
                add(report, 'truncated-why', f'{cat}: {title}')

if x_topics != EXPECTED_X:
    add(report, 'x-order', f'Expected {EXPECTED_X}; got {x_topics}')

for why, count in why_counts.most_common(10):
    if count >= 5:
        add(report, 'canned-why', f'Repeated {count} times: {why[:180]}')

report['status'] = 'fail' if report['failures'] else 'pass'
OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({
    'status': report['status'],
    'totalItems': report['totalItems'],
    'categoryCounts': report['categoryCounts'],
    'failures': len(report['failures']),
    'warnings': len(report['warnings']),
}, indent=2))
if report['failures']:
    for row in report['failures'][:50]:
        print(f"FAIL [{row['kind']}] {row['message']}")
    raise SystemExit(f"V5 final content audit failed with {len(report['failures'])} issue(s).")
print('V5 FINAL CONTENT AUDIT PASS')
