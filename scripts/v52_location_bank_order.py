#!/usr/bin/env python3
"""Location-bank-aware ordering for V5.2 B2.

Local is a nationwide inventory bank and is filtered by market in the browser.
A category-wide source ladder can create meaningless cross-market publisher
streaks (for example many CBS affiliates next to each other) even when each
market is healthy. This pass preserves every Local item and every marketId,
preserves the relative ranked order inside each market as much as possible,
and interleaves markets so the serialized bank is source-diverse too.

No category ownership, content, or UX is changed.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from pathlib import Path

NEWS = Path("News")
REPORT = Path("/tmp/v52-location-bank-order.json")


def field(item, name):
    return (item.findtext(name) or "").strip()


def source_id(value):
    s = re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    aliases = {
        "apnews": "associatedpress",
        "associatedpressnews": "associatedpress",
        "krqecom": "krqe",
        "bbcnews": "bbc",
        "bbccom": "bbc",
    }
    return aliases.get(s, s or "unknown")


def max_streak(items):
    best = cur = 0
    last = None
    best_source = ""
    for item in items:
        src = source_id(field(item, "source"))
        if src == last:
            cur += 1
        else:
            last = src
            cur = 1
        if cur > best:
            best = cur
            best_source = src
    return {"count": best, "source": best_source}


def market_key(item):
    return field(item, "marketId") or field(item, "market") or field(item, "locationId") or "__unknown__"


def source_rank(item):
    try:
        return int(field(item, "v52SourceRank") or "1000")
    except Exception:
        return 1000


def article_rank(item):
    try:
        return int(field(item, "v52ArticleRank") or "9999")
    except Exception:
        return 9999


def rebalance_market(rows):
    """Round-robin sources inside one market, preserving per-source story rank."""
    buckets = defaultdict(list)
    first_pos = {}
    for pos, item in enumerate(rows):
        sid = source_id(field(item, "source"))
        buckets[sid].append(item)
        first_pos.setdefault(sid, pos)
    for sid in buckets:
        buckets[sid].sort(key=lambda x: (article_rank(x), first_pos[sid]))
    source_order = sorted(buckets, key=lambda sid: (
        min(source_rank(x) for x in buckets[sid]),
        first_pos[sid],
    ))
    out = []
    round_no = 0
    while True:
        added = 0
        for sid in source_order:
            if round_no < len(buckets[sid]):
                out.append(buckets[sid][round_no])
                added += 1
        if not added:
            break
        round_no += 1
    return out


def interleave_markets(grouped, market_order):
    """Interleave market queues while avoiding same-source adjacency when possible."""
    queues = {m: deque(grouped[m]) for m in market_order if grouped[m]}
    out = []
    last_source = None
    while queues:
        chosen = None
        # Prefer the first market whose next item changes publisher.
        for m in market_order:
            q = queues.get(m)
            if q and source_id(field(q[0], "source")) != last_source:
                chosen = m
                break
        if chosen is None:
            chosen = next(m for m in market_order if m in queues and queues[m])
        item = queues[chosen].popleft()
        out.append(item)
        last_source = source_id(field(item, "source"))
        if not queues[chosen]:
            del queues[chosen]
    return out


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel missing")

    items = list(channel.findall("item"))
    local = [x for x in items if field(x, "category").lower() == "local"]
    if not local:
        REPORT.write_text(json.dumps({"localCount": 0}, indent=2) + "\n", encoding="utf-8")
        return

    grouped = defaultdict(list)
    market_order = []
    for item in local:
        m = market_key(item)
        if m not in grouped:
            market_order.append(m)
        grouped[m].append(item)

    before_global = max_streak(local)
    before_market = {m: max_streak(rows) for m, rows in grouped.items()}
    rebalanced = {m: rebalance_market(rows) for m, rows in grouped.items()}
    ordered_local = interleave_markets(rebalanced, market_order)
    after_global = max_streak(ordered_local)
    after_market = {m: max_streak(rows) for m, rows in rebalanced.items()}

    # Replace the Local block at its first original position, preserving all
    # non-Local category ordering exactly.
    rebuilt = []
    inserted = False
    for item in items:
        if field(item, "category").lower() == "local":
            if not inserted:
                rebuilt.extend(ordered_local)
                inserted = True
            continue
        rebuilt.append(item)

    for item in items:
        channel.remove(item)
    for item in rebuilt:
        channel.append(item)
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)

    report = {
        "localCount": len(local),
        "marketCount": len(grouped),
        "inventoryPreserved": len(ordered_local) == len(local),
        "globalSourceStreakBefore": before_global,
        "globalSourceStreakAfter": after_global,
        "maxPerMarketStreakBefore": max((v["count"] for v in before_market.values()), default=0),
        "maxPerMarketStreakAfter": max((v["count"] for v in after_market.values()), default=0),
        "unknownMarketItems": len(grouped.get("__unknown__", [])),
        "method": "per-market source round-robin + cross-market interleave",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
