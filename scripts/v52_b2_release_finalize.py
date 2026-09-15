#!/usr/bin/env python3
"""Final B2 release pass.

Runs after source ladders and D-pool removals so the serialized News feed is the
exact order audited and rendered. It does two deliberately narrow things:

1. Removes exact Legislation duplicates by normalized title or canonical URL.
2. Prevents a deep single-publisher tail after other source ladders are
   exhausted. The cap is applied only to editorial tabs where a single source
   can otherwise dominate the bottom of the feed. Local/Region are excluded
   because their inventory is viewer-location scoped.

This pass never changes category ownership and never changes the UX.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

NEWS = Path("News")
REPORT = Path("/tmp/v52-b2-finalize.json")

# A source may keep several strong stories, but it may not become the entire
# tail of a tab once the other publisher ladders are exhausted.
SOURCE_CAPS = {
    "top": 3,
    "world": 6,
    "us": 5,
    "presidential": 6,
    "federal": 5,
    "nm": 6,
    "nfl": 8,          # current feed has very few non-ESPN sources; preserves >=10 cards
    "technology": 6,
    "gaming": 6,
    "military": 6,
    "entertainment": 6,
}


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
    # Match the audit's exact-title normalization so a duplicate cannot pass
    # the finalizer and then fail the release gate.
    s = re.sub(r"\s+-\s+[^-]{2,50}$", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def norm_url(value):
    try:
        p = urlsplit(value or "")
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))
    except Exception:
        return value or ""


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel missing")

    items = list(channel.findall("item"))
    kept = []
    removed = []
    source_counts = defaultdict(Counter)
    leg_titles = set()
    leg_urls = set()

    for item in items:
        cat = field(item, "category").lower()
        src = source_id(field(item, "source"))

        if cat == "legislation":
            nt = norm_title(field(item, "title"))
            nu = norm_url(field(item, "link"))
            duplicate = (nt and nt in leg_titles) or (nu and nu in leg_urls)
            if duplicate:
                removed.append({
                    "category": cat,
                    "source": field(item, "source"),
                    "title": field(item, "title"),
                    "reason": "exact-legislation-duplicate",
                })
                continue
            if nt:
                leg_titles.add(nt)
            if nu:
                leg_urls.add(nu)

        cap = SOURCE_CAPS.get(cat)
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
        "sourceCaps": SOURCE_CAPS,
        "removed": removed[:100],
        "locationScopedTabsUncapped": ["local", "region"],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
