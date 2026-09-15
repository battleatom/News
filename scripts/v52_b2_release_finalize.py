#!/usr/bin/env python3
"""Final B2 release pass.

Runs after source ladders, D-pool removals, and location-bank ordering so the
serialized News feed is the exact order audited and rendered.

This pass deliberately does only two editorial-safety jobs:
1. Deduplicate Legislation by official record identity first, then canonical
   official URL. Normalized title is only a fallback when no official identity
   exists, so distinct bills with similar titles are never collapsed together.
2. Prevent deep single-publisher tails. World, Presidential, and New Mexico use
   proportional caps so strong inventory is retained while one source cannot
   dominate the whole tab. NFL remains adaptive when source diversity is sparse.

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

# Fixed caps are appropriate where there is normally enough source breadth.
BASE_SOURCE_CAPS = {
    "top": 3,
    "us": 5,
    "federal": 5,
    "nfl": 8,
    "technology": 6,
    "gaming": 6,
    "military": 6,
    "entertainment": 6,
}

# These tabs can legitimately have one wire/local publisher carrying many of
# the strongest stories. Keep up to 35% of the candidate tab from one source,
# with a floor of six, instead of throwing away useful inventory at six cards.
PROPORTIONAL_SOURCE_CAPS = {
    "world": 0.35,
    "presidential": 0.35,
    "nm": 0.35,
}
PROPORTIONAL_FLOOR = 6


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
    """Return the strongest available identity for an official record."""
    bill = norm_identity(field(item, "billNumber"))
    jurisdiction = norm_identity(field(item, "jurisdiction"))
    source = source_id(field(item, "source"))
    if bill:
        return f"bill:{jurisdiction or source}:{bill}"
    official = norm_url(field(item, "officialSource") or field(item, "link"))
    if official:
        return f"url:{official}"
    title = norm_title(field(item, "title"))
    return f"title:{source}:{title}" if title else ""


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
        caps.pop("nfl", None)
    return caps, len(nfl_sources), dict(category_counts)


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
    leg_identities = set()
    leg_urls = set()

    for item in items:
        cat = field(item, "category").lower()
        src = source_id(field(item, "source"))

        if cat == "legislation":
            ident = legislation_identity(item)
            official_url = norm_url(field(item, "officialSource") or field(item, "link"))
            duplicate = (ident and ident in leg_identities) or (official_url and official_url in leg_urls)
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
            if official_url:
                leg_urls.add(official_url)

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
        kept.append(item)

    for item in items:
        channel.remove(item)
    for item in kept:
        channel.append(item)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    report = {
        "input": len(items),
        "output": len(kept),
        "removedCount": len(removed),
        "removedByReason": dict(Counter(x["reason"] for x in removed)),
        "sourceCaps": source_caps,
        "configuredFixedSourceCaps": BASE_SOURCE_CAPS,
        "proportionalSourceCaps": PROPORTIONAL_SOURCE_CAPS,
        "proportionalFloor": PROPORTIONAL_FLOOR,
        "categoryCountsBeforeFinalizer": category_counts,
        "nflQualifiedSourceCount": nfl_source_count,
        "nflAdaptiveCap": "uncapped-low-diversity" if "nfl" not in source_caps else source_caps["nfl"],
        "legislationDedupPolicy": "billNumber+jurisdiction, then canonical official URL, title only when identity is unavailable",
        "removed": removed[:100],
        "locationScopedTabsUncapped": ["local", "region"],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
