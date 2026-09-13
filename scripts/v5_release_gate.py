#!/usr/bin/env python3
"""Fail closed when a generated V5 feed/site is not safe to freeze.

V5 keeps the useful V4 structural checks, but its public Entertainment surface is
Clean-only. Dirty records may remain in the backing feed for classification/history;
they are not a release-volume requirement and adult-industry volume is never used as
a readiness signal.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / 'News'
INDEX = ROOT / 'index.html'
VERIFY = ROOT / 'verification-report.json'
ENT_ASSET = ROOT / 'assets' / 'entertainment-v4.js'

MIN_COUNTS = {
    'top':20,'nfl':10,'underreported':20,'world':15,'us':15,
    'presidential':15,'federal':5,'legislation':10,'nm':15,
    'local':40,'region':15,'technology':8,'gaming':10,'military':15,
}
EXPECTED_X = [
    'Health','Technology & AI','Celebrities & Public Figures','World',
    'Politics & Government','Entertainment','Sports','Business & Economy',
    'Gaming','Science'
]
ADULT_LABELS = {'ADULT INDUSTRY','ADULT BUSINESS/LEGAL','CREATOR','ADULT AWARDS'}
SENSITIVE_IMAGE_LABELS = ADULT_LABELS | {'NUDE / PHOTO SHOOT'}


def text(node, tag):
    return (node.findtext(tag) or '').strip()


def fail(message):
    raise SystemExit(f'V5 RELEASE GATE FAILED: {message}')


def main():
    if not NEWS.exists() or not INDEX.exists():
        fail('generated News/index.html artifacts are missing')
    items = ET.parse(NEWS).getroot().findall('.//item')
    if not items:
        fail('feed contains zero items')

    counts = Counter(text(i,'category') for i in items)
    for category, minimum in MIN_COUNTS.items():
        if counts.get(category,0) < minimum:
            fail(f'{category} has {counts.get(category,0)} stories; minimum is {minimum}')

    malformed = [text(i,'title') or '<untitled>' for i in items if not text(i,'title') or not text(i,'link') or not text(i,'category')]
    if malformed:
        fail(f'{len(malformed)} malformed item(s) lack title/link/category')

    underreported = [i for i in items if text(i,'category') == 'underreported']
    underreported_links = {text(i,'link') for i in underreported if text(i,'link')}

    entertainment = [i for i in items if text(i,'category') == 'entertainment']
    clean = [i for i in entertainment if text(i,'entertainmentSafety') == 'clean']
    dirty = [i for i in entertainment if text(i,'entertainmentSafety') == 'dirty']
    adult = [i for i in dirty if text(i,'entertainmentLabel') in ADULT_LABELS]
    if len(clean) < 10:
        fail(f'Clean Entertainment has {len(clean)} stories; minimum is 10')
    if len(clean) + len(dirty) != len(entertainment):
        fail('Entertainment contains unclassified or overlapping safety records')

    cross_links = 0
    for item in entertainment:
        title = text(item,'title')
        if not text(item,'entertainmentLabel') or not text(item,'entertainmentScore'):
            fail(f'Entertainment ranking metadata missing for: {title}')
        if not text(item,'guid'):
            fail(f'Entertainment GUID missing for: {title}')
        if text(item,'entertainmentLabel') in SENSITIVE_IMAGE_LABELS and text(item,'imageUrl'):
            fail(f'Sensitive Entertainment preview image was not suppressed: {title}')
        for article in item.findall('./underreportedLinks/article'):
            target = text(article,'link')
            if not target or target not in underreported_links:
                fail(f'Entertainment cross-link does not point to retained Underreported story: {title}')
            cross_links += 1

    x_items = [i for i in items if text(i,'category') == 'x']
    x_topics = [text(i,'xTopic') for i in x_items]
    if x_topics != EXPECTED_X:
        fail(f'X topics are not the fixed ten-topic sequence: {x_topics}')

    legislation = [i for i in items if text(i,'category') == 'legislation']
    if any(not text(i,'link') for i in legislation):
        fail('Legislation contains a record without an official link')

    if VERIFY.exists():
        report = json.loads(VERIFY.read_text(encoding='utf-8'))
        residual = report.get('residualStrongDuplicatePairs',[])
        if residual:
            fail(f'verification report contains {len(residual)} residual strong duplicate pair(s)')

    html = INDEX.read_text(encoding='utf-8')
    if html.count('assets/entertainment-v4.js') != 1:
        fail('Entertainment UI must be injected exactly once')
    if 'assets/location-content-v25.js' not in html:
        fail('location content controller is missing from generated site')
    if not ENT_ASSET.exists() or 'DIRTY_UI_ENABLED=false' not in ENT_ASSET.read_text(encoding='utf-8'):
        fail('public Entertainment surface is not locked to Clean-only mode')

    print('V5 RELEASE GATE PASSED')
    print('Feed items:', len(items))
    print('Category counts:', dict(sorted(counts.items())))
    print('Entertainment backing feed: clean', len(clean), 'dirty', len(dirty), 'adult', len(adult), 'cross-links', cross_links)
    print('Public Entertainment mode: Clean-only')
    print('X topics:', x_topics)


if __name__ == '__main__':
    main()
