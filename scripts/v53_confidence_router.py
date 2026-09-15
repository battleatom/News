#!/usr/bin/env python3
"""Conservative V5.3 category-confidence router.

Purpose:
- act on V5.3 low-confidence flags without reverting to brittle keyword filters;
- reroute only when a specialist destination is a clearly stronger fit;
- otherwise down-rank weak-fit stories within their existing publisher slots;
- never delete stories or touch protected/special tabs.

This layer is intentionally conservative. It only routes into specialist tabs
(Technology, Gaming, NFL, Military, Entertainment) when the destination score is
high and beats the current category by a wide margin. Broad civic/geographic
categories are never chosen as automatic destinations.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import v53_quality_layer as q

NEWS = Path("News")
REPORT = Path("/tmp/v53-routing-report.json")

PROTECTED = {"top", "underreported", "legislation", "local", "region", "nm", "x"}
ROUTABLE_FROM = {"world", "us", "presidential", "federal", "nfl", "technology", "gaming", "military", "entertainment"}
SPECIALIST_DESTINATIONS = ("technology", "gaming", "nfl", "military", "entertainment")

LOW_CONFIDENCE = 55
DESTINATION_MIN = 74
MIN_MARGIN = 24
DOWNRANK_PENALTY = 12

SPECIALISTS = {
    "nfl": {"nflcom","espn","cbssports","nbcsports","foxsports","yahoosports","profootballtalk","theathletic"},
    "technology": {"arstechnica","theverge","wired","techcrunch","ieeespectrum","mittechnologyreview","tomshardware","cnet","zdnet","engadget"},
    "gaming": {"ign","pcgamer","gamespot","polygon","eurogamer","nintendolife","kotaku","vgc","gamesindustrybiz","rockpapershotgun"},
    "military": {"defensenews","breakingdefense","militarytimes","thewarzone","usninews","starsandstripes","taskpurpose"},
    "entertainment": {"variety","hollywoodreporter","deadline","billboard","rollingstone","entertainmentweekly","people","pitchfork","vulture"},
}

# Stronger signals than a single generic word. Phrases are weighted more heavily
# and are combined with publisher specialty and existing article context.
WEIGHTED_TERMS = {
    "technology": {
        "artificial intelligence": 16, "cybersecurity": 16, "ransomware": 16,
        "software": 10, "hardware": 10, "semiconductor": 14, "chip": 8,
        "iphone": 12, "android": 12, "windows": 10, "macos": 12,
        "steamos": 14, "nvidia": 12, "apple": 8, "google": 7,
        "microsoft": 8, "openai": 12, "data center": 10, "cloud": 7,
    },
    "gaming": {
        "video game": 18, "gaming": 14, "gameplay": 16, "playstation": 16,
        "xbox": 16, "nintendo": 16, "switch": 12, "steam game": 16,
        "dlc": 16, "esports": 16, "console": 10, "game studio": 14,
    },
    "nfl": {
        "nfl": 20, "super bowl": 18, "touchdown": 14, "quarterback": 14,
        "wide receiver": 14, "running back": 14, "roster": 10,
        "football": 8, "chiefs": 10, "cowboys": 10, "broncos": 10,
    },
    "military": {
        "pentagon": 16, "military": 14, "army": 10, "navy": 10,
        "air force": 12, "marines": 12, "warship": 16, "fighter jet": 16,
        "missile": 12, "troops": 12, "drone attack": 12, "defense ministry": 12,
    },
    "entertainment": {
        "box office": 16, "hollywood": 14, "movie": 10, "film": 9,
        "television": 10, "tv series": 12, "actor": 10, "actress": 10,
        "album": 10, "singer": 10, "emmy": 14, "grammy": 14, "oscar": 14,
    },
}


def text(item, tag):
    return (item.findtext(tag) or "").strip()


def set_tag(item, tag, value):
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = str(value)


def category_score(item, cat: str) -> int:
    hay = q.body_text(item).lower()
    src = q.norm_source(text(item, "source"))
    base = 42
    # Reuse the quality layer's broad semantic vocabulary.
    broad_hits = sum(1 for term in q.CATEGORY_TERMS.get(cat, ()) if term in hay)
    base += min(24, broad_hits * 6)
    # Add stronger phrase/topic evidence.
    weighted = sum(weight for term, weight in WEIGHTED_TERMS.get(cat, {}).items() if term in hay)
    base += min(30, weighted)
    if src in SPECIALISTS.get(cat, set()):
        base += 16
    return max(0, min(100, base))


def current_score(item, cat: str) -> int:
    try:
        stored = int(float(text(item, "categoryConfidence") or 0))
    except Exception:
        stored = 0
    # Use the stronger of the existing V5.3 score and this router's score so a
    # route only happens when the current category is genuinely weak.
    return max(stored, category_score(item, cat))


def adjusted_quality(item) -> float:
    try:
        base = float(text(item, "v53QualityScore") or 0)
    except Exception:
        base = 0.0
    action = text(item, "v53RoutingAction")
    if action == "downrank":
        return base - DOWNRANK_PENALTY
    return base


def reorder_same_source_pattern(items):
    """Down-rank within a publisher while keeping that category's source sequence."""
    buckets = defaultdict(list)
    pattern = []
    for pos, item in enumerate(items):
        sid = q.norm_source(text(item, "source"))
        pattern.append(sid)
        buckets[sid].append((pos, item))
    for sid, arr in buckets.items():
        arr.sort(key=lambda p: (-adjusted_quality(p[1]), p[0]))
    offsets = Counter()
    out = []
    for sid in pattern:
        idx = offsets[sid]
        out.append(buckets[sid][idx][1])
        offsets[sid] += 1
    return out


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    items = list(channel.findall("item"))
    original_count = len(items)
    original_categories = Counter(text(i, "category").lower() for i in items)
    decisions = []
    rerouted = []
    downranked = []

    for item in items:
        cat = text(item, "category").lower()
        if cat in PROTECTED or cat not in ROUTABLE_FROM:
            set_tag(item, "v53RoutingAction", "protected")
            continue

        cur = current_score(item, cat)
        candidates = []
        for dest in SPECIALIST_DESTINATIONS:
            if dest == cat:
                continue
            score = category_score(item, dest)
            candidates.append((score, dest))
        candidates.sort(reverse=True)
        best_score, best_dest = candidates[0]
        margin = best_score - cur

        set_tag(item, "v53RoutingCurrentScore", cur)
        set_tag(item, "v53RoutingBestCategory", best_dest)
        set_tag(item, "v53RoutingBestScore", best_score)
        set_tag(item, "v53RoutingMargin", margin)

        if cur < LOW_CONFIDENCE and best_score >= DESTINATION_MIN and margin >= MIN_MARGIN:
            old = cat
            set_tag(item, "category", best_dest)
            # Preserve a trace of origin for audits and future tuning.
            set_tag(item, "v53OriginalCategory", old)
            set_tag(item, "v53RoutingAction", "reroute")
            rec = {
                "title": text(item, "title"), "source": text(item, "source"),
                "from": old, "to": best_dest, "currentScore": cur,
                "destinationScore": best_score, "margin": margin,
            }
            rerouted.append(rec); decisions.append(rec)
        elif cur < LOW_CONFIDENCE:
            set_tag(item, "v53RoutingAction", "downrank")
            rec = {
                "title": text(item, "title"), "source": text(item, "source"),
                "category": cat, "currentScore": cur, "bestCategory": best_dest,
                "bestScore": best_score, "margin": margin,
            }
            downranked.append(rec); decisions.append(rec)
        else:
            set_tag(item, "v53RoutingAction", "keep")

    # Rebuild category blocks and down-rank weak-fit stories only within each
    # publisher's slots. This avoids broad source-order churn.
    by_cat = defaultdict(list)
    cat_order = []
    seen = set()
    for item in items:
        cat = text(item, "category").lower()
        if cat not in seen:
            seen.add(cat); cat_order.append(cat)
        by_cat[cat].append(item)

    for item in list(channel.findall("item")):
        channel.remove(item)
    for cat in cat_order:
        for item in reorder_same_source_pattern(by_cat[cat]):
            channel.append(item)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    final_count = len(channel.findall("item"))
    final_categories = Counter(text(i, "category").lower() for i in channel.findall("item"))

    report = {
        "model": "v53-confidence-router-conservative",
        "thresholds": {
            "lowConfidenceBelow": LOW_CONFIDENCE,
            "destinationMinimum": DESTINATION_MIN,
            "minimumMargin": MIN_MARGIN,
            "downrankPenalty": DOWNRANK_PENALTY,
        },
        "storyCountBefore": original_count,
        "storyCountAfter": final_count,
        "hardDeletes": original_count - final_count,
        "protectedCategories": sorted(PROTECTED),
        "automaticDestinations": list(SPECIALIST_DESTINATIONS),
        "reroutedCount": len(rerouted),
        "downrankedCount": len(downranked),
        "rerouted": rerouted[:100],
        "downranked": downranked[:100],
        "categoryCountsBefore": dict(original_categories),
        "categoryCountsAfter": dict(final_categories),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
