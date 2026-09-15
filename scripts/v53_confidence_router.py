#!/usr/bin/env python3
"""Conservative V5.3 category-confidence router.

Purpose:
- act on V5.3 low-confidence flags without brittle one-word filters;
- reroute only when a specialist destination is a clearly stronger fit;
- otherwise down-rank weak-fit stories inside their current publisher slots;
- never delete stories or touch protected/special tabs;
- refuse reroutes that would create an exact/near duplicate in the destination.

This runs only in the isolated V5.3 quality-lab branch.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from difflib import SequenceMatcher
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
NEAR_DUPLICATE_RATIO = 0.90

SPECIALISTS = {
    "nfl": {"nflcom","espn","cbssports","nbcsports","foxsports","yahoosports","profootballtalk","theathletic"},
    "technology": {"arstechnica","theverge","wired","techcrunch","ieeespectrum","mittechnologyreview","tomshardware","cnet","zdnet","engadget"},
    "gaming": {"ign","pcgamer","gamespot","polygon","eurogamer","nintendolife","kotaku","vgc","gamesindustrybiz","rockpapershotgun"},
    "military": {"defensenews","breakingdefense","militarytimes","thewarzone","usninews","starsandstripes","taskpurpose"},
    "entertainment": {"variety","hollywoodreporter","deadline","billboard","rollingstone","entertainmentweekly","people","pitchfork","vulture"},
}

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


def normalized_title(item):
    value = text(item, "title").lower()
    # Collector titles commonly append " - publisher"; remove that transport suffix.
    value = re.sub(r"\s+-\s+[^-]{2,80}$", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def category_score(item, cat: str) -> int:
    hay = q.body_text(item).lower()
    src = q.norm_source(text(item, "source"))
    base = 42
    broad_hits = sum(1 for term in q.CATEGORY_TERMS.get(cat, ()) if term in hay)
    base += min(24, broad_hits * 6)
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
    return max(stored, category_score(item, cat))


def adjusted_quality(item) -> float:
    try:
        base = float(text(item, "v53QualityScore") or 0)
    except Exception:
        base = 0.0
    return base - DOWNRANK_PENALTY if text(item, "v53RoutingAction") == "downrank" else base


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


def collides_with_destination(item, destination, destination_items):
    """Return True when moving item would duplicate an existing destination story."""
    needle = normalized_title(item)
    if not needle:
        return False
    for other in destination_items.get(destination, ()):
        if other is item:
            continue
        candidate = normalized_title(other)
        if not candidate:
            continue
        if needle == candidate:
            return True
        # Near-title blocking is limited to meaningful headlines to avoid short-title noise.
        if min(len(needle), len(candidate)) >= 32 and SequenceMatcher(None, needle, candidate).ratio() >= NEAR_DUPLICATE_RATIO:
            return True
    return False


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    items = list(channel.findall("item"))
    original_count = len(items)
    original_categories = Counter(text(i, "category").lower() for i in items)
    original_by_cat = defaultdict(list)
    for item in items:
        original_by_cat[text(item, "category").lower()].append(item)

    rerouted = []
    downranked = []
    collision_blocked = []

    for item in items:
        cat = text(item, "category").lower()
        if cat in PROTECTED or cat not in ROUTABLE_FROM:
            set_tag(item, "v53RoutingAction", "protected")
            continue

        cur = current_score(item, cat)
        candidates = []
        for dest in SPECIALIST_DESTINATIONS:
            if dest != cat:
                candidates.append((category_score(item, dest), dest))
        candidates.sort(reverse=True)
        best_score, best_dest = candidates[0]
        margin = best_score - cur

        set_tag(item, "v53RoutingCurrentScore", cur)
        set_tag(item, "v53RoutingBestCategory", best_dest)
        set_tag(item, "v53RoutingBestScore", best_score)
        set_tag(item, "v53RoutingMargin", margin)

        qualifies = cur < LOW_CONFIDENCE and best_score >= DESTINATION_MIN and margin >= MIN_MARGIN
        if qualifies and collides_with_destination(item, best_dest, original_by_cat):
            set_tag(item, "v53RoutingAction", "downrank")
            rec = {
                "title": text(item, "title"), "source": text(item, "source"),
                "from": cat, "to": best_dest, "currentScore": cur,
                "destinationScore": best_score, "margin": margin,
                "reason": "destination duplicate collision",
            }
            collision_blocked.append(rec)
            downranked.append({
                "title": text(item, "title"), "source": text(item, "source"),
                "category": cat, "currentScore": cur, "bestCategory": best_dest,
                "bestScore": best_score, "margin": margin,
                "reason": "reroute blocked by duplicate guard",
            })
        elif qualifies:
            old = cat
            set_tag(item, "category", best_dest)
            set_tag(item, "v53OriginalCategory", old)
            set_tag(item, "v53RoutingAction", "reroute")
            rerouted.append({
                "title": text(item, "title"), "source": text(item, "source"),
                "from": old, "to": best_dest, "currentScore": cur,
                "destinationScore": best_score, "margin": margin,
            })
        elif cur < LOW_CONFIDENCE:
            set_tag(item, "v53RoutingAction", "downrank")
            downranked.append({
                "title": text(item, "title"), "source": text(item, "source"),
                "category": cat, "currentScore": cur, "bestCategory": best_dest,
                "bestScore": best_score, "margin": margin,
            })
        else:
            set_tag(item, "v53RoutingAction", "keep")

    by_cat = defaultdict(list)
    cat_order = []
    seen = set()
    for item in items:
        cat = text(item, "category").lower()
        if cat not in seen:
            seen.add(cat)
            cat_order.append(cat)
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
        "model": "v53-confidence-router-conservative-collision-safe",
        "thresholds": {
            "lowConfidenceBelow": LOW_CONFIDENCE,
            "destinationMinimum": DESTINATION_MIN,
            "minimumMargin": MIN_MARGIN,
            "downrankPenalty": DOWNRANK_PENALTY,
            "nearDuplicateRatio": NEAR_DUPLICATE_RATIO,
        },
        "storyCountBefore": original_count,
        "storyCountAfter": final_count,
        "hardDeletes": original_count - final_count,
        "protectedCategories": sorted(PROTECTED),
        "automaticDestinations": list(SPECIALIST_DESTINATIONS),
        "reroutedCount": len(rerouted),
        "downrankedCount": len(downranked),
        "collisionBlockedCount": len(collision_blocked),
        "rerouted": rerouted[:100],
        "downranked": downranked[:100],
        "collisionBlocked": collision_blocked[:100],
        "categoryCountsBefore": dict(original_categories),
        "categoryCountsAfter": dict(final_categories),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
