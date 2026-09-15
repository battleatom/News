#!/usr/bin/env python3
"""Final B2 release pass.

Runs after source ladders, D-pool removals, and location-bank ordering so the
serialized News feed is the exact order audited and rendered.

Editorial-safety jobs:
1. Deduplicate Legislation by authoritative bill identity. For numbered bills,
   jurisdiction + billNumber is the only duplicate key; shared legislature links
   never collapse distinct bills. URL/title fallback is used only when billNumber
   is missing.
2. Limit source dominance without throwing away healthy inventory. Tabs whose
   strongest publisher legitimately carries many stories use proportional caps.
3. Smooth retained source depth across the whole tab instead of leaving a dominant
   publisher in a deep-scroll tail. Per-source story order remains intact.
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

BASE_SOURCE_CAPS = {
    "top": 3,
    "technology": 6,
    "gaming": 6,
    "entertainment": 6,
    "nfl": 8,
}

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


def theoretical_streak_bound(rows):
    counts = Counter(source_id(field(x, "source")) for x in rows)
    if not counts:
        return 0
    largest = max(counts.values())
    others = len(rows) - largest
    return max(1, int(math.ceil(largest / (others + 1))))


def max_source_streak(rows):
    best = cur = 0
    last = None
    for item in rows:
        sid = source_id(field(item, "source"))
        if sid == last:
            cur += 1
        else:
            last = sid
            cur = 1
        best = max(best, cur)
    return best


def smooth_sources(rows):
    """Evenly distribute publishers while preserving story order inside each source."""
    if len(rows) < 2:
        return list(rows)

    buckets = defaultdict(list)
    first_pos = {}
    for pos, item in enumerate(rows):
        sid = source_id(field(item, "source"))
        buckets[sid].append(item)
        first_pos.setdefault(sid, pos)

    total = len(rows)
    scheduled = []
    for sid, bucket in buckets.items():
        count = len(bucket)
        for idx, item in enumerate(bucket):
            ideal = ((idx + 0.5) * total) / count
            scheduled.append((ideal, first_pos[sid], idx, sid, item))
    scheduled.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    out = [x[4] for x in scheduled]

    target = theoretical_streak_bound(rows)
    if max_source_streak(out) <= target:
        return out

    queues = {sid: list(bucket) for sid, bucket in buckets.items()}
    source_order = sorted(queues, key=lambda sid: first_pos[sid])
    rebuilt = []
    last = None
    run = 0
    emitted = Counter()
    while any(queues.values()):
        candidates = [sid for sid in source_order if queues[sid]]
        allowed = [sid for sid in candidates if not (sid == last and run >= target)] or candidates
        chosen = max(
            allowed,
            key=lambda sid: (
                len(queues[sid]) / max(1, len(buckets[sid])),
                -emitted[sid],
                -first_pos[sid],
            ),
        )
        item = queues[chosen].pop(0)
        rebuilt.append(item)
        emitted[chosen] += 1
        if chosen == last:
            run += 1
        else:
            last = chosen
            run = 1
    return rebuilt


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
    leg_fallback_urls = set()
    leg_fallback_titles = set()

    for item in items:
        cat = field(item, "category").lower()
        src = source_id(field(item, "source"))

        if cat == "legislation":
            ident, has_bill_identity = legislation_identity(item)
            official_url = norm_url(field(item, "officialSource") or field(item, "link"))
            render_title = norm_title(field(item, "title"))

            if has_bill_identity:
                duplicate = bool(ident and ident in leg_identities)
            else:
                duplicate = bool(
                    (ident and ident in leg_identities)
                    or (official_url and official_url in leg_fallback_urls)
                    or (render_title and render_title in leg_fallback_titles)
                )
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
            if not has_bill_identity:
                if official_url:
                    leg_fallback_urls.add(official_url)
                if render_title:
                    leg_fallback_titles.add(render_title)

        cat_max = CATEGORY_MAX.get(cat)
        if cat_max is not None and category_kept[cat] >= cat_max:
            removed.append({"category": cat, "source": field(item, "source"), "title": field(item, "title"), "reason": f"category-release-cap-{cat_max}"})
            continue

        cap = source_caps.get(cat)
        if cap is not None and source_counts[cat][src] >= cap:
            removed.append({"category": cat, "source": field(item, "source"), "title": field(item, "title"), "reason": f"source-depth-cap-{cap}"})
            continue

        source_counts[cat][src] += 1
        category_kept[cat] += 1
        kept.append(item)

    rebalance_tabs = set(source_caps) - {"local", "region", "legislation"}
    grouped = defaultdict(list)
    for item in kept:
        grouped[field(item, "category").lower()].append(item)

    streak_before = {}
    streak_after = {}
    streak_targets = {}
    for cat in rebalance_tabs:
        rows = grouped.get(cat, [])
        streak_before[cat] = max_source_streak(rows)
        streak_targets[cat] = theoretical_streak_bound(rows)
        grouped[cat] = smooth_sources(rows)
        streak_after[cat] = max_source_streak(grouped[cat])

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
        "legislationDedupPolicy": "numbered bills dedupe only by jurisdiction+billNumber; URL/title fallback only when billNumber is absent",
        "sourceStreakBeforeSmoothing": streak_before,
        "sourceStreakAfterSmoothing": streak_after,
        "sourceStreakTargets": streak_targets,
        "rebalancedTabs": sorted(rebalance_tabs),
        "removed": removed[:100],
        "locationScopedTabsUncapped": ["local", "region"],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
