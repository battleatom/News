#!/usr/bin/env python3
"""Conservative cross-tab duplicate guard.

Collapses only obvious duplicate coverage across ordinary subject tabs: identical URLs,
near-identical headlines, or very strong headline+description overlap. Editorial/ranking
surfaces remain independent. Removed copies are preserved as relatedArticles on the
strongest primary card and a machine-readable report is emitted.
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROUTABLE = {
    'world','us','presidential','federal','nm','local','region',
    'technology','gaming','military','nfl'
}
# More specific destinations win ties so a federal story does not survive as generic US.
CATEGORY_PRIORITY = {
    'local': 90, 'nm': 85, 'presidential': 82, 'federal': 80, 'nfl': 80,
    'gaming': 76, 'technology': 74, 'military': 72, 'region': 68,
    'us': 55, 'world': 50,
}
STOP = {
    'the','a','an','and','or','but','to','of','in','on','for','from','with','at','by',
    'as','is','are','was','were','be','been','being','this','that','these','those',
    'it','its','after','before','over','into','about','new','says','said','news','live'
}


def clean(v: str | None) -> str:
    return re.sub(r'\s+', ' ', v or '').strip()


def category(item: ET.Element) -> str:
    return clean(item.findtext('category')).lower()


def title(item: ET.Element) -> str:
    raw = clean(item.findtext('title'))
    return re.sub(r'\s+(?:[-–—|:]\s*)?(?:Reuters|AP News|Associated Press|BBC|CNN|Fox News|NBC News|ABC News|CBS News|NPR|USA Today)\s*$', '', raw, flags=re.I)


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r'[a-z0-9]+', text.lower()) if len(w) >= 3 and w not in STOP}


def canonical_url(raw: str) -> str:
    raw = clean(raw)
    if not raw:
        return ''
    try:
        p = urlsplit(raw)
        host = p.netloc.lower().removeprefix('www.')
        path = re.sub(r'/+$', '', p.path) or '/'
        return urlunsplit((p.scheme.lower() or 'https', host, path, '', ''))
    except Exception:
        return raw.lower()


def strong_duplicate(a: ET.Element, b: ET.Element) -> tuple[bool, str]:
    if category(a) == category(b):
        return False, ''
    if category(a) not in ROUTABLE or category(b) not in ROUTABLE:
        return False, ''
    ua, ub = canonical_url(a.findtext('link') or ''), canonical_url(b.findtext('link') or '')
    if ua and ua == ub:
        return True, 'same-url'
    ta, tb = tokens(title(a)), tokens(title(b))
    if not ta or not tb:
        return False, ''
    shared = len(ta & tb)
    title_ratio = shared / max(1, min(len(ta), len(tb)))
    if min(len(ta), len(tb)) >= 5 and shared >= 5 and title_ratio >= .88:
        return True, 'near-identical-title'
    da = tokens(clean(a.findtext('description')))
    db = tokens(clean(b.findtext('description')))
    if len(da) >= 10 and len(db) >= 10:
        body_shared = len(da & db)
        body_ratio = body_shared / max(1, min(len(da), len(db)))
        if shared >= 4 and title_ratio >= .72 and body_shared >= 8 and body_ratio >= .82:
            return True, 'strong-title-body-overlap'
    return False, ''


def score(item: ET.Element) -> tuple[int, int, int]:
    return (
        CATEGORY_PRIORITY.get(category(item), 0),
        min(len(clean(item.findtext('description'))), 2000),
        min(len(title(item)), 180),
    )


def related_key(node: ET.Element) -> str:
    return canonical_url(node.findtext('link') or '') or title(node).lower()


def attach_related(primary: ET.Element, other: ET.Element) -> bool:
    rel = primary.find('relatedArticles')
    if rel is None:
        rel = ET.SubElement(primary, 'relatedArticles')
    existing = {related_key(x) for x in rel.findall('article')}
    key = related_key(other)
    if not key or key in existing:
        return False
    ar = ET.SubElement(rel, 'article')
    for tag in ('title','link','source','pubDate'):
        value = clean(other.findtext(tag))
        if value:
            ET.SubElement(ar, tag).text = value
    ET.SubElement(ar, 'crossTabFrom').text = category(other)
    return True


def clusters(items: list[ET.Element]) -> tuple[list[list[int]], list[dict]]:
    parent = list(range(len(items)))
    reasons: dict[tuple[int,int], str] = {}
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i, a in enumerate(items):
        if category(a) not in ROUTABLE:
            continue
        for j in range(i + 1, len(items)):
            b = items[j]
            dup, reason = strong_duplicate(a, b)
            if dup:
                union(i, j)
                reasons[(i,j)] = reason
    grouped: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        grouped[find(i)].append(i)
    dup_groups = [g for g in grouped.values() if len(g) > 1]
    pairs = [
        {'a': title(items[i]), 'aCategory': category(items[i]), 'b': title(items[j]),
         'bCategory': category(items[j]), 'reason': reason}
        for (i,j), reason in reasons.items()
    ]
    return dup_groups, pairs


def run(feed: Path, report_path: Path, apply: bool) -> dict:
    tree = ET.parse(feed)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('Invalid RSS: missing channel')
    items = list(channel.findall('item'))
    before = Counter(category(i) for i in items)
    groups, pairs = clusters(items)
    removed: set[int] = set()
    attached = 0
    cluster_report = []
    for group in groups:
        winner = max(group, key=lambda idx: score(items[idx]))
        primary = items[winner]
        removed_rows = []
        for idx in group:
            if idx == winner:
                continue
            if attach_related(primary, items[idx]):
                attached += 1
            removed.add(idx)
            removed_rows.append({'title': title(items[idx]), 'category': category(items[idx])})
        cluster_report.append({
            'kept': title(primary), 'primaryCategory': category(primary),
            'removed': removed_rows, 'size': len(group)
        })
    final_items = [item for idx, item in enumerate(items) if idx not in removed]
    after = Counter(category(i) for i in final_items)
    drops = {cat: before[cat] - after[cat] for cat in sorted(ROUTABLE) if before[cat] != after[cat]}
    excessive = {
        cat: {'before': before[cat], 'after': after[cat]}
        for cat in ROUTABLE if before[cat] >= 10 and after[cat] < max(8, int(before[cat] * .75))
    }
    if excessive:
        raise SystemExit('Cross-tab dedupe would over-prune categories: ' + json.dumps(excessive, sort_keys=True))
    if apply:
        for item in list(channel.findall('item')):
            channel.remove(item)
        for item in final_items:
            channel.append(item)
        tree.write(feed, encoding='utf-8', xml_declaration=True)
    residual_groups, residual_pairs = clusters(final_items)
    report = {
        'mode': 'apply' if apply else 'dry-run',
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'inputArticles': len(items), 'outputArticles': len(final_items),
        'crossTabPairsDetected': len(pairs), 'crossTabDuplicatesRemoved': len(removed),
        'supportingLinksAttached': attached, 'categoryDrops': drops,
        'clusters': cluster_report, 'residualStrongCrossTabPairs': residual_pairs,
        'policy': {
            'scope': sorted(ROUTABLE),
            'editorialSurfacesExcluded': ['top','underreported','x','boxoffice','legislation','entertainment'],
            'matching': ['same-url','near-identical-title','strong-title-body-overlap'],
            'maxCategoryReduction': '25% for pools with at least 10 stories',
        },
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Cross-tab integrity: {len(items)} -> {len(final_items)} articles; {len(removed)} obvious duplicates removed")
    print('Category drops:', dict(drops))
    if residual_groups:
        raise SystemExit(f'{len(residual_groups)} strong cross-tab duplicate cluster(s) remain')
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--feed', default='News')
    p.add_argument('--report', default='cross-tab-integrity-report.json')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    run(Path(args.feed), Path(args.report), args.apply)


if __name__ == '__main__':
    main()
