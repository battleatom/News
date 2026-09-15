#!/usr/bin/env python3
"""Final B2 release pass.

Runs after source ladders, D-pool removals, and location-bank ordering so the
serialized News feed is the exact order audited and rendered.

Editorial-safety jobs:
1. Deduplicate Legislation by bill identity first. Shared agency/index URLs are
   never allowed to collapse distinct bill numbers.
2. Limit source dominance without throwing away healthy inventory. Tabs whose
   strongest publisher legitimately carries many stories use proportional caps.
3. Rebalance the retained capped tabs after filtering so source diversity is
   distributed through the whole list instead of forming a one-source tail.
4. Keep NFL adaptive when qualified source diversity is sparse, with a 25-story
   release ceiling so one-source recovery cannot flood the tab.

This pass never changes category ownership and never changes the UX.
"""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

NEWS = Path("News")
REPORT = Path("/tmp/v52-b2-finalize.json")

# Fixed caps are appropriate where the candidate pool normally has broad source depth.
BASE_SOURCE_CAPS = {
    "top": 3,
    "technology": 6,
    "gaming": 6,
    "entertainment": 6,
    "nfl": 8,
}

# These tabs can legitimately have a wire/specialist/local publisher carrying a
# large share of the strongest stories. Proportional caps preserve inventory while
# still preventing pathological dominance. A final round-robin spreads the retained
# source depth through the list rather than leaving a one-publisher tail.
PROPORTIONAL_SOURCE_CAPS = {
    "world": 0.55,
    "presidential": 0.55,
    "nm": 0.45,
    "us": 0.45,
    "federal": 0.35,
    "military": 0.45,
}
PROPORTIONAL_FLOOR = 6
NFL_LOW_DIVERSITY_SOURCE_CAP = 24
CATEGORY_MAX = {"nfl": 25}


def field(item, name):
    return (item.findtext(name) or "").strip()


def source_id(value):
    s = re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    aliases = {
        "apnews": "associatedpress",
        "associatedpressnews": "associatedpress",
        "bbcnews": "bbc",
        "bbccom": "bbc",
        "theguardian": "guardian",
        "krqecom": "krqe",
        "wiredcom": "wired",
    }
    return aliases.get(s, s or "unknown")


def norm_title(value):
    s = (value or "").lower()
    s = re.sub(r"\s+-\s+[^-]{2,50}$", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def norm_identity(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def norm_url(value):
    try:
        p = urlsplit(value or "")
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))
    except Exception:
        return value or ""


def legislation_identity(item):
    """Return the strongest available official-record identity."""
    bill = norm_identity(field(item, "billNumber"))
    jurisdiction = norm_identity(field(item, "jurisdiction"))
    source = source_id(field(item, "source"))
    if bill:
        return f"bill:{jurisdiction or source}:{bill}", True
    official = norm_url(field(item, "officialSource") or field(item, "link"))
    if official:
        return f"url:{official}", False
    title = norm_title(field(item, "title"))
    return (f"title:{source}:{title}" if title else ""), False


def effective_source_caps(items):
    caps = dict(BASE_SOURCE_CAPS)
    category_counts = Counter(field(item, "category").lower() for item in items)
    for cat, fraction in PROPORTIONAL_SOURCE_CAPS.items():
        total = category_counts.get(cat, 0)
        if total:
            caps[cat] = max(PROPORTIONAL_FLOOR, int(math.ceil(total * fraction)))

    nfl_sources = {
        source_id(field(item, "source"))
        for item in items
        if field(item, "category").lower() == "nfl"
    }
    if len(nfl_sources) < 3:
        caps["nfl"] = NFL_LOW_DIVERSITY_SOURCE_CAP
    return caps, len(nfl_sources), dict(category_counts)


def rebalance_sources(rows):
    """Round-robin retained publishers while preserving per-source story order."""
    if len(rows) < 2:
        return list(rows)
    buckets = defaultdict(list)
    first_pos = {}
    for pos, item in enumerate(rows):
        sid = source_id(field(item, "source"))
        buckets[sid].append(item)
        first_pos.setdefault(sid, pos)
    order = sorted(buckets, key=lambda sid: first_pos[sid])
    out = []
    round_no = 0
    while True:
        added = 0
        for sid in order:
            if round_no < len(buckets[sid]):
                out.append(buckets[sid][round_no])
                added += 1
        if not added:
            break
        round_no += 1
    return out


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel missing")

    items = list(channel.findall("item"))
    source_caps, nfl_source_count, category_counts = effective_source_caps(items)
    kept = []
    removed = []
    source_counts = defaultdict(Counter)
    category_kept = Counter()
    leg_identities = set()
    leg_urls_without_bill = set()

    for item in items:
        cat = field(item, "category").lower()
        src = source_id(field(item, "source"))

        if cat == "legislation":
            ident, has_bill_identity = legislation_identity(item)
            official_url = norm_url(field(item, "officialSource") or field(item, "link"))
            # A bill number + jurisdiction/source is authoritative. Distinct bills may
            # legitimately share the same legislature index URL, so URL equality is
            # considered only for records that do not have a bill identity.
            if has_bill_identity:
                duplicate = bool(ident and ident in leg_identities)
            else:
                duplicate = bool((ident and ident in leg_identities) or (official_url and official_url in leg_urls_without_bill))
            if duplicate:
                removed.append({
                    "category": cat,
                    "source": field(item, "source"),
                    "title": field(item, "title"),
                    "billNumber": field(item, "billNumber"),
                    "reason": "official-legislation-identity-duplicate",
                })
                continue
            if ident:
                leg_identities.add(ident)
            if official_url and not has_bill_identity:
                leg_urls_without_bill.add(official_url)

        cat_max = CATEGORY_MAX.get(cat)
        if cat_max is not None and category_kept[cat] >= cat_max:
            removed.append({
                "category": cat,
                "source": field(item, "source"),
                "title": field(item, "title"),
                "reason": f"category-release-cap-{cat_max}",
            })
            continue

        cap = source_caps.get(cat)
        if cap is not None and source_counts[cat][src] >= cap:
            removed.append({
                "category": cat,
                "source": field(item, "source"),
                "title": field(item, "title"),
                "reason": f"source-depth-cap-{cap}",
            })
            continue

        source_counts[cat][src] += 1
        category_kept[cat] += 1
        kept.append(item)

    # Rebalance only source-capped global tabs. Local/Region remain location-bank
    # ordered, Underreported has its own ranking, and Legislation preserves official order.
    rebalance_tabs = set(source_caps) - {"local", "region", "legislation"}
    grouped = defaultdict(list)
    for item in kept:
        grouped[field(item, "category").lower()].append(item)
    for cat in rebalance_tabs:
        grouped[cat] = rebalance_sources(grouped.get(cat, []))

    rebuilt = []
    emitted = set()
    for item in kept:
        cat = field(item, "category").lower()
        if cat in rebalance_tabs:
            if cat not in emitted:
                rebuilt.extend(grouped[cat])
                emitted.add(cat)
            continue
        rebuilt.append(item)

    for item in items:
        channel.remove(item)
    for item in rebuilt:
        channel.append(item)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    report = {
        "input": len(items),
        "output": len(rebuilt),
        "removedCount": len(removed),
        "removedByReason": dict(Counter(x["reason"] for x in removed)),
        "sourceCaps": source_caps,
        "configuredFixedSourceCaps": BASE_SOURCE_CAPS,
        "proportionalSourceCaps": PROPORTIONAL_SOURCE_CAPS,
        "proportionalFloor": PROPORTIONAL_FLOOR,
        "categoryMax": CATEGORY_MAX,
        "categoryCountsBeforeFinalizer": category_counts,
        "categoryCountsAfterFinalizer": dict(Counter(field(x, "category").lower() for x in rebuilt)),
        "nflQualifiedSourceCount": nfl_source_count,
        "nflAdaptiveCap": source_caps.get("nfl"),
        "legislationDedupPolicy": "billNumber+jurisdiction/source is authoritative; shared URLs dedupe only records without bill identity",
        "rebalancedTabs": sorted(rebalance_tabs),
        "removed": removed[:100],
        "locationScopedTabsUncapped": ["local", "region"],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
