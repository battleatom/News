#!/usr/bin/env python3
"""Collapse the same U.S. political event across US/Presidential/Federal tabs.

The normal verifier clusters within one category. This pass handles the adjacent
political surfaces as one family so a single event does not appear as multiple full
cards in multiple tabs. Removed cards are preserved as Coverage links.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import verify_feed as vf
from source_priority import source_priority

NEWS = Path("News")
POLITICAL_SURFACES = {"us", "presidential", "federal"}


def cross_same_event(a: ET.Element, b: ET.Element) -> bool:
    if vf.category(a) not in POLITICAL_SURFACES or vf.category(b) not in POLITICAL_SURFACES:
        return False
    if not vf.legacy.looks_english(a) or not vf.legacy.looks_english(b):
        return False
    if vf.syndicated_copy(a, b) or vf.near_exact_title(a, b):
        return True

    groups = vf.event_groups(a) & vf.event_groups(b)
    if not groups:
        return False

    amounts = vf.amount_keys(a) & vf.amount_keys(b)
    actors = vf.actor_keys(a) & vf.actor_keys(b)
    entities = vf.entity_keys(a) & vf.entity_keys(b)
    shared = vf.specific_tokens(a) & vf.specific_tokens(b)
    title_shared = vf.title_specific_tokens(a) & vf.title_specific_tokens(b)

    # Very strong generic event signatures. No politician/topic is hard-coded.
    if amounts and (actors or entities) and groups:
        return True
    if amounts and len(shared) >= 2 and groups:
        return True
    if (actors or entities) and len(title_shared) >= 3 and len(shared) >= 4:
        return True
    if len(title_shared) >= 5 and len(shared) >= 6:
        return True
    return False


def primary_score(item: ET.Element) -> tuple:
    # Source standards first, then freshness/completeness. Ideology is not scored.
    return (
        source_priority(item.findtext("source")),
        vf.parsed_time(item),
        min(len(vf.clean(item.findtext("description"))), 1400),
        min(len(vf.title(item)), 160),
    )


def add_article(rel: ET.Element, article: ET.Element) -> bool:
    existing = {
        ((x.findtext("link") or "").strip() or (x.findtext("title") or "").strip()).lower()
        for x in rel.findall("article")
    }
    key = ((article.findtext("link") or "").strip() or (article.findtext("title") or "").strip()).lower()
    if not key or key in existing:
        return False
    ar = ET.SubElement(rel, "article")
    for tag in ("title", "link", "source", "pubDate"):
        value = (article.findtext(tag) or "").strip()
        if value:
            ET.SubElement(ar, tag).text = value
    return True


def attach_all(primary: ET.Element, other: ET.Element) -> int:
    rel = primary.find("relatedArticles")
    if rel is None:
        rel = ET.SubElement(primary, "relatedArticles")
    count = 1 if add_article(rel, other) else 0
    nested = other.find("relatedArticles")
    if nested is not None:
        for article in nested.findall("article"):
            count += 1 if add_article(rel, article) else 0
    return count


def clusters(rows: list[ET.Element]) -> list[list[int]]:
    parent = list(range(len(rows)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(rows):
        for j in range(i + 1, len(rows)):
            if cross_same_event(a, rows[j]):
                union(i, j)

    out: dict[int, list[int]] = defaultdict(list)
    for i in range(len(rows)):
        out[find(i)].append(i)
    return list(out.values())


def main() -> None:
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")

    all_items = list(channel.findall("item"))
    rows = [i for i in all_items if vf.category(i) in POLITICAL_SURFACES]
    removed_ids: set[int] = set()
    cluster_count = 0
    support_count = 0

    for group in clusters(rows):
        if len(group) < 2:
            continue
        members = [rows[i] for i in group]
        primary = max(members, key=primary_score)
        cluster_count += 1
        for other in members:
            if other is primary:
                continue
            support_count += attach_all(primary, other)
            removed_ids.add(id(other))

    for item in list(channel.findall("item")):
        if id(item) in removed_ids:
            channel.remove(item)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(
        f"Political cross-tab clustering: {cluster_count} cluster(s), "
        f"{len(removed_ids)} duplicate card(s) removed, {support_count} coverage link(s) preserved."
    )


if __name__ == "__main__":
    main()
