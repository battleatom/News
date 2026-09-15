#!/usr/bin/env python3
"""Conservative topic-spacing pass for Technology and Gaming.

Preserves every story and the existing editorial order as much as possible. When
an upcoming card repeats a strong product/company/topic from one of the previous
four displayed cards, it is deferred until a different topic can be shown.
Nothing is deleted and the pass does not globally re-rank the feed.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

NEWS = Path("News")
REPORT = Path("/tmp/v531-topic-spacing-report.json")
TARGETS = {"technology", "gaming"}
WINDOW = 4

STRONG_PHRASES = (
    "openai", "chatgpt", "anthropic", "claude", "nvidia", "geforce", "microsoft", "windows 11",
    "apple", "iphone", "ios 27", "macos", "google", "pixel", "android", "samsung", "galaxy",
    "meta", "facebook", "instagram", "whatsapp", "tiktok", "tesla", "spacex",
    "nintendo switch 2", "switch 2", "nintendo", "playstation", "ps5", "xbox game pass", "xbox",
    "steam frame", "steam deck", "steam", "valve", "epic games", "battle.net",
    "007 first light", "james bond", "persona", "zelda", "metroid", "runescape", "diablo",
)

STOP = {
    "the","and","for","with","from","into","about","after","before","this","that","these","those",
    "new","news","latest","update","updates","report","reports","says","said","will","could","would","should",
    "how","why","what","when","where","who","your","our","their","its","has","have","had","was","were",
    "are","is","to","of","in","on","at","by","as","a","an","or","but","not","more","most","best",
    "technology","tech","gaming","game","games","review","reviews","first","look","watch","video",
    "release","releases","released","coming","available","edition","year","years","2026","2027",
}


def text(item, tag):
    return (item.findtext(tag) or "").strip()


def title(item):
    return text(item, "title")


def category(item):
    return text(item, "category").lower()


def fingerprint(item):
    raw = title(item).lower()
    strong = {p for p in STRONG_PHRASES if p in raw}
    words = {
        w for w in re.findall(r"[a-z0-9]+", raw)
        if len(w) >= 4 and w not in STOP
    }
    return strong, words


def similarity(a, b):
    sa, wa = fingerprint(a)
    sb, wb = fingerprint(b)
    shared_strong = sa & sb
    if shared_strong:
        # A shared named company/product/topic is sufficient for spacing.
        return 1.0
    if not wa or not wb:
        return 0.0
    shared = wa & wb
    # For non-curated tokens require multiple meaningful title terms; this avoids
    # treating generic words like "release" or "game" as the same topic.
    if len(shared) < 2:
        return 0.0
    return len(shared) / max(1, min(len(wa), len(wb)))


def conflicts(candidate, recent):
    return any(similarity(candidate, prev) >= 0.50 for prev in recent)


def spaced(items):
    """Keep baseline order, only skipping forward when a recent topic conflicts."""
    remaining = list(items)
    out = []
    while remaining:
        recent = out[-WINDOW:]
        pick = 0
        for idx, candidate in enumerate(remaining):
            if not conflicts(candidate, recent):
                pick = idx
                break
        out.append(remaining.pop(pick))
    return out


def conflict_count(items, limit=25):
    arr = items[:limit]
    count = 0
    examples = []
    for i, item in enumerate(arr):
        recent = arr[max(0, i-WINDOW):i]
        matches = [(p, similarity(item, p)) for p in recent]
        matches = [(p, s) for p, s in matches if s >= 0.50]
        if matches:
            count += 1
            p, s = max(matches, key=lambda x: x[1])
            if len(examples) < 12:
                examples.append({"story": title(item), "near": title(p), "similarity": round(s, 2)})
    return count, examples


def displacement(before, after, limit=25):
    old = {id(item): i for i, item in enumerate(before)}
    moves = [abs(i-old[id(item)]) for i,item in enumerate(after[:limit])]
    return round(sum(moves)/len(moves),2) if moves else 0


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")
    items = list(channel.findall("item"))
    by_cat = defaultdict(list)
    for item in items:
        by_cat[category(item)].append(item)

    replacements = {}
    report = {"policy":{"targets":sorted(TARGETS),"window":WINDOW,"deletes":0,"ranking":"preserve baseline; defer only recent-topic conflicts"},"tabs":{}}
    for cat in TARGETS:
        before = by_cat.get(cat, [])
        after = spaced(before)
        replacements[cat] = iter(after)
        bc, be = conflict_count(before)
        ac, ae = conflict_count(after)
        report["tabs"][cat] = {
            "count":len(before),
            "beforeWindowConflictsTop25":bc,
            "afterWindowConflictsTop25":ac,
            "improvement":bc-ac,
            "averageTop25Displacement":displacement(before,after),
            "beforeTop25":[title(x) for x in before[:25]],
            "afterTop25":[title(x) for x in after[:25]],
            "beforeExamples":be,
            "afterExamples":ae,
        }

    for item in items:
        channel.remove(item)
    for item in items:
        cat=category(item)
        channel.append(next(replacements[cat]) if cat in TARGETS else item)

    tree.write(NEWS,encoding="utf-8",xml_declaration=True)
    REPORT.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
