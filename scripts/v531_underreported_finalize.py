#!/usr/bin/env python3
"""V5.3.1 final Underreported ordering.

Assumes v53_underreported_guard.py has already validated evidence. Keeps the same
eligible stories and moves the highest public-impact stories to the top.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

from underreported_priority import importance_score

NEWS = Path("News")
REPORT = Path("/tmp/v531-underreported-finalize.json")


def text(item, tag):
    return (item.findtext(tag) or "").strip()


def number(item, tag):
    try:
        return int(float(text(item, tag) or 0))
    except Exception:
        return 0


def date_value(item):
    try:
        return parsedate_to_datetime(text(item, "pubDate")).timestamp()
    except Exception:
        return 0


def set_text(item, tag, value):
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = str(value)


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")
    items = list(channel.findall("item"))
    under = [x for x in items if text(x, "category").lower() == "underreported"]

    bad = [text(x, "title") for x in under if not (1 <= number(x, "recentSupportingSourceCount") <= 8)]
    if bad:
        raise SystemExit(f"Underreported evidence guard incomplete; invalid recent-source counts: {bad[:5]}")

    before = [text(x, "title") for x in under]
    for item in under:
        set_text(item, "underreportedImpactScore", importance_score(item))
    under.sort(key=lambda x: (
        number(x, "underreportedImpactScore"),
        number(x, "underreportedPriority"),
        number(x, "underreportedScore"),
        date_value(x),
    ), reverse=True)

    top = [x for x in items if text(x, "category").lower() == "top"]
    rest = [x for x in items if text(x, "category").lower() not in {"top", "underreported"}]
    for item in list(channel.findall("item")):
        channel.remove(item)
    for item in top + under + rest:
        channel.append(item)
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)

    report = {
        "count": len(under),
        "invalidRecentSourceCounts": 0,
        "ordering": "public impact > underreporting priority > signal > recency",
        "beforeTop10": before[:10],
        "afterTop10": [text(x, "title") for x in under[:10]],
        "afterTop10Detail": [
            {"impact": number(x, "underreportedImpactScore"), "support": number(x, "recentSupportingSourceCount"), "title": text(x, "title")}
            for x in under[:10]
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
