#!/usr/bin/env python3
from __future__ import annotations

import difflib
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from verify_feed import category, representative_score, title

NEWS = Path('News')


def title_key(value: str) -> str:
    value = re.sub(
        r'\s+(?:[-–—|:]\s*)?(?:Reuters|AP News|Associated Press|BBC|CNN|Fox News|NBC News|ABC News|CBS News|NPR|USA Today|IGN(?: Nordic)?|GameSpot|PC Gamer|Polygon)\s*$',
        '', value, flags=re.I,
    )
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def likely_same_title(a: str, b: str) -> bool:
    ka, kb = title_key(a), title_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    wa, wb = set(ka.split()), set(kb.split())
    smaller = min(len(wa), len(wb))
    if smaller >= 5 and len(wa & wb) / smaller >= 0.86:
        return True
    return min(len(ka), len(kb)) >= 35 and difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.92


def clusters(items: list[ET.Element]) -> list[list[int]]:
    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_cat: dict[str, list[int]] = defaultdict(list)
    for i, item in enumerate(items):
        by_cat[category(item)].append(i)

    for indices in by_cat.values():
        for pos, i in enumerate(indices):
            for j in indices[pos + 1:]:
                if likely_same_title(title(items[i]), title(items[j])):
                    union(i, j)

    grouped: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        grouped[find(i)].append(i)
    return list(grouped.values())


def remaining_pairs(items: list[ET.Element]) -> list[tuple[str, str, str]]:
    out = []
    by_cat: dict[str, list[ET.Element]] = defaultdict(list)
    for item in items:
        by_cat[category(item)].append(item)
    for cat, group in by_cat.items():
        for pos, a in enumerate(group):
            for b in group[pos + 1:]:
                if likely_same_title(title(a), title(b)):
                    out.append((cat, title(a), title(b)))
    return out


def main() -> None:
    tree = ET.parse(NEWS)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('Invalid RSS: missing channel')

    items = list(channel.findall('item'))
    remove: set[int] = set()
    removed = 0
    cluster_count = 0

    for group in clusters(items):
        if len(group) <= 1:
            continue
        cluster_count += 1
        keep = max(group, key=lambda i: representative_score(items[i]))
        for i in group:
            if i != keep:
                remove.add(i)
                removed += 1

    if remove:
        for item in list(channel.findall('item')):
            channel.remove(item)
        final = [item for i, item in enumerate(items) if i not in remove]
        for item in final:
            channel.append(item)
        tree.write(NEWS, encoding='utf-8', xml_declaration=True)
    else:
        final = items

    residual = remaining_pairs(final)
    print(f'Final semantic dedupe removed {removed} article(s) across {cluster_count} cluster(s).')
    print(f'Residual audit-level duplicate pairs: {len(residual)}')
    for cat, a, b in residual[:10]:
        print(f'  [{cat}] {a} || {b}')
    if residual:
        raise SystemExit('Audit-level duplicate pairs remain after final semantic dedupe.')


if __name__ == '__main__':
    main()
