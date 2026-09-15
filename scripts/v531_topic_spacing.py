#!/usr/bin/env python3
"""V5.3.1 topic-spacing pass for Technology and Gaming.

Preserves every story. It only changes order inside the two target categories so
near-duplicate topics do not sit back-to-back. Higher-impact/high-quality stories
remain favored; topic repetition adds a temporary placement penalty rather than
causing deletion.
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

STOP = {
    "the","and","for","with","from","into","about","after","before","this","that","these","those",
    "new","news","latest","update","updates","report","reports","says","said","will","could","would","should",
    "how","why","what","when","where","who","your","our","their","its","has","have","had","was","were",
    "are","is","to","of","in","on","at","by","as","a","an","or","but","not","more","most","best",
    "technology","tech","gaming","game","games","review","reviews","hands","first","look","watch","video",
}

GENERIC = {
    "ai","software","hardware","computer","computing","console","pc","mobile","app","apps","device","devices",
    "release","launch","announced","announcement","available","support","feature","features","update","updates",
}

IMPACT_TERMS = {
    "breach":18,"cyberattack":20,"hack":16,"hacked":16,"security":10,"privacy":10,"surveillance":12,
    "outage":16,"recall":16,"ban":14,"lawsuit":13,"court":12,"ruling":13,"regulation":12,"antitrust":14,
    "layoffs":12,"acquisition":11,"merger":11,"shutdown":13,"vulnerability":16,"exploit":17,"malware":17,
    "ransomware":20,"data":4,"chips":8,"semiconductor":8,"tariff":10,"government":8,"military":8,
    "nintendo":4,"playstation":4,"xbox":4,"steam":4,"switch":4,"gpu":5,"iphone":4,"android":4,
}

PHRASES = (
    "switch 2","playstation 5","ps5","xbox series","steam deck","steam os","steam machine","geforce rtx",
    "windows 11","windows 12","iphone 17","iphone 18","galaxy s","pixel 10","openai","chatgpt",
    "artificial intelligence","data center","data breach","cyber attack","cyberattack","game pass",
)


def text(item, tag):
    return (item.findtext(tag) or "").strip()


def title(item):
    return text(item, "title")


def category(item):
    return text(item, "category").lower()


def quality(item):
    try:
        return float(text(item, "v53QualityScore"))
    except Exception:
        return 50.0


def impact(item):
    hay = f"{title(item)} {text(item, 'description')} {text(item, 'whyMatters')}".lower()
    score = quality(item)
    for term, weight in IMPACT_TERMS.items():
        if re.search(r"\b" + re.escape(term) + r"\b", hay):
            score += weight
    if re.search(r"\b(deal|sale|discount|coupon|best|guide|review|trailer|teaser)\b", title(item).lower()):
        score -= 12
    return score


def fingerprint(item):
    raw = title(item).lower()
    fp = set()
    for phrase in PHRASES:
        if phrase in raw:
            fp.add(phrase.replace(" ", "_"))
    words = [w for w in re.findall(r"[a-z0-9]+", raw) if len(w) >= 3 and w not in STOP]
    for w in words:
        if w not in GENERIC:
            fp.add(w)
    # Named/product tokens are especially useful for topic identity.
    return fp


def similarity(a, b):
    fa, fb = fingerprint(a), fingerprint(b)
    if not fa or not fb:
        return 0.0
    shared = fa & fb
    if not shared:
        return 0.0
    # One strong product/entity token can be enough for a repeated topic when the
    # smaller title has few meaningful tokens; otherwise require broader overlap.
    ratio = len(shared) / max(1, min(len(fa), len(fb)))
    if any("_" in token for token in shared):
        ratio = max(ratio, 0.80)
    return ratio


def conflicts(candidate, recent):
    return any(similarity(candidate, prev) >= 0.50 for prev in recent)


def spaced(items):
    remaining = list(items)
    out = []
    while remaining:
        recent = out[-WINDOW:]
        ranked = sorted(
            enumerate(remaining),
            key=lambda pair: (-impact(pair[1]), pair[0]),
        )
        clean = [pair for pair in ranked if not conflicts(pair[1], recent)]
        pick_idx, picked = (clean[0] if clean else ranked[0])
        out.append(picked)
        remaining.pop(pick_idx)
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
            if len(examples) < 10:
                examples.append({"story": title(item), "near": title(p), "similarity": round(s, 2)})
    return count, examples


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
    report = {"policy": {"targets": sorted(TARGETS), "window": WINDOW, "deletes": 0}, "tabs": {}}
    for cat in TARGETS:
        before = by_cat.get(cat, [])
        after = spaced(before)
        replacements[cat] = iter(after)
        before_conflicts, before_examples = conflict_count(before)
        after_conflicts, after_examples = conflict_count(after)
        report["tabs"][cat] = {
            "count": len(before),
            "beforeWindowConflictsTop25": before_conflicts,
            "afterWindowConflictsTop25": after_conflicts,
            "improvement": before_conflicts - after_conflicts,
            "beforeTop25": [title(x) for x in before[:25]],
            "afterTop25": [title(x) for x in after[:25]],
            "beforeExamples": before_examples,
            "afterExamples": after_examples,
            "top5ImpactBefore": sorted([(round(impact(x),2), title(x)) for x in before], reverse=True)[:5],
            "top5ImpactAfterPositions": [
                {"position": next((i+1 for i, y in enumerate(after) if y is x), None), "impact": round(impact(x),2), "title": title(x)}
                for x in sorted(before, key=impact, reverse=True)[:5]
            ],
        }

    for item in items:
        channel.remove(item)
    for item in items:
        cat = category(item)
        if cat in TARGETS:
            channel.append(next(replacements[cat]))
        else:
            channel.append(item)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
