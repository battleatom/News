#!/usr/bin/env python3
"""Consolidate same-event coverage inside each tab and preserve removed stories as related links.

This is intentionally topic-agnostic. It uses title anchors, numeric/date fingerprints,
shared event groups, and title-token overlap rather than one-off filters for named events.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import verify_feed as vf

NEWS = Path('News')
MAX_RELATED = 6


def clean(v):
    return vf.clean(v)


def category(item):
    return vf.category(item)


def title(item):
    return vf.title(item)


def title_tokens(item):
    return vf.title_specific_tokens(item)


def fingerprint_keys(item):
    text = f"{title(item)} {clean(item.findtext('description'))}".lower()
    out = set(vf.amount_keys(item))
    for m in re.findall(r'\b(?:0?[1-9]|1[0-2])\s*[/-]\s*(?:0?[1-9]|[12][0-9]|3[01])\b', text):
        out.add('date:' + re.sub(r'\s+', '', m))
    for m in re.findall(r'\b(?:9\s*/\s*11|9-11|september\s+11(?:th)?)\b', text):
        out.add('date:9/11')
    for raw in re.findall(r'\b\d{4,}\b', text):
        try:
            n = int(raw)
        except ValueError:
            continue
        if not 1900 <= n <= 2100:
            out.add(f'num:{n}')
    return out


def expanded_same_event(a, b):
    if category(a) != category(b):
        return False
    if vf.same_event(a, b):
        return True
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return False
    shared = ta & tb
    overlap = len(shared) / max(1, min(len(ta), len(tb)))
    fps = fingerprint_keys(a) & fingerprint_keys(b)
    groups = vf.event_groups(a) & vf.event_groups(b)
    entities = vf.entity_keys(a) & vf.entity_keys(b)

    # Distinctive number/date + one shared topical anchor is strong evidence.
    if fps and len(shared) >= 1:
        return True
    # Same named subject/event family plus multiple title anchors.
    if entities and len(shared) >= 2 and (groups or overlap >= 0.45):
        return True
    # General same-event coverage without named entities.
    if groups and len(shared) >= 3 and overlap >= 0.45:
        return True
    # Very high title-semantic overlap can stand alone.
    if len(shared) >= 4 and overlap >= 0.58:
        return True
    return False


def representative_score(item):
    return vf.representative_score(item)


def related_node(item):
    return {
        'title': clean(item.findtext('title')),
        'link': clean(item.findtext('link')),
        'source': clean(item.findtext('source')),
        'pubDate': clean(item.findtext('pubDate')),
        'description': clean(item.findtext('description')),
    }


def attach_related(kept, removed_items):
    existing = kept.find('relatedArticles')
    if existing is None:
        existing = ET.SubElement(kept, 'relatedArticles')
    seen = set()
    for node in existing.findall('article'):
        key = (clean(node.findtext('link')) or clean(node.findtext('title'))).lower()
        if key:
            seen.add(key)
    added = 0
    for item in sorted(removed_items, key=representative_score, reverse=True):
        row = related_node(item)
        key = (row['link'] or row['title']).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ar = ET.SubElement(existing, 'article')
        for tag in ('title', 'link', 'source', 'pubDate', 'description'):
            ET.SubElement(ar, tag).text = row[tag]
        added += 1
        if len(existing.findall('article')) >= MAX_RELATED:
            break
    if not existing.findall('article'):
        kept.remove(existing)
    return added


def cluster(items):
    parent = list(range(len(items)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a,b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_cat = defaultdict(list)
    for i, item in enumerate(items):
        if category(item) != 'legislation':
            by_cat[category(item)].append(i)
    for indices in by_cat.values():
        for p, i in enumerate(indices):
            for j in indices[p+1:]:
                if expanded_same_event(items[i], items[j]):
                    union(i,j)
    groups = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)
    return list(groups.values())


def run(path=NEWS):
    tree = ET.parse(path)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('Invalid RSS: missing channel')
    items = list(channel.findall('item'))
    remove = set()
    clusters = 0
    related_added = 0
    for group in cluster(items):
        if len(group) <= 1:
            continue
        members = [items[i] for i in group]
        best_index = max(group, key=lambda i: representative_score(items[i]))
        kept = items[best_index]
        removed = [items[i] for i in group if i != best_index]
        related_added += attach_related(kept, removed)
        for i in group:
            if i != best_index:
                remove.add(i)
        clusters += 1
    if remove:
        for i, item in enumerate(items):
            if i in remove:
                channel.remove(item)
    tree.write(path, encoding='utf-8', xml_declaration=True)
    print(f'Event consolidation: {len(remove)} duplicate card(s) folded into {clusters} event(s); {related_added} supporting link(s) attached.')
    return {'removed': len(remove), 'clusters': clusters, 'relatedAdded': related_added}


if __name__ == '__main__':
    run()
