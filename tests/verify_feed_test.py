#!/usr/bin/env python3
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_feed as vf


def item(title: str, category: str, source: str = "Reuters", description: str = "") -> ET.Element:
    node = ET.Element("item")
    ET.SubElement(node, "title").text = title
    ET.SubElement(node, "description").text = description or (
        title + ". The story is part of a developing national issue and officials are reviewing the details."
    )
    ET.SubElement(node, "source").text = source
    ET.SubElement(node, "category").text = category
    ET.SubElement(node, "link").text = "https://example.com/" + str(abs(hash((title, category, source))))
    ET.SubElement(node, "pubDate").text = "Thu, 10 Sep 2026 20:00:00 GMT"
    return node


def main() -> None:
    # Event dedupe is category-aware but available in every tab.
    for cat in ["top", "underreported", "world", "us", "presidential", "federal", "legislation", "nm", "local", "region", "technology", "gaming", "military", "nfl"]:
        a = item("Acme announces $5,000 payment program after federal vote", cat)
        b = item("$5,000 payments from Acme move forward following vote", cat)
        assert vf.same_event(a, b), f"same event not detected in {cat}"

    # Same real-world event may remain in separate genuinely relevant tabs.
    a = item("Acme announces $5,000 payment program after federal vote", "us")
    b = item("Acme announces $5,000 payment program after federal vote", "presidential")
    assert not vf.same_event(a, b), "cross-tab event should not be deleted globally"

    # Calendar years must not become numeric event fingerprints.
    year_story = item("Acme outlines its 2026 technology roadmap", "technology")
    assert "num:2026" not in vf.amount_keys(year_story), "year incorrectly used as event amount"

    # Distinctive money amounts remain event anchors.
    money_story = item("Acme approves $5,000 payment", "us")
    assert "usd:5000" in vf.amount_keys(money_story), "currency amount missing from fingerprint"

    # Representative selection must prefer stronger sources over arrival order.
    weak = item("Acme announces $5,000 payment program", "us", "Local Daily")
    strong = item("Acme announces $5,000 payment program", "us", "Reuters")
    assert vf.representative_score(strong) > vf.representative_score(weak), "source ranking did not prefer Reuters"

    # Different events involving the same prominent person should survive.
    iran = item("Trump discusses Iran ceasefire after missile attacks", "presidential")
    border = item("Trump announces new border immigration rules", "presidential")
    assert not vf.same_event(iran, border), "unrelated stories about same person were collapsed"

    # Cluster engine should collapse multiple members of one event.
    stories = [
        item("Acme announces $5,000 payment program after federal vote", "us"),
        item("$5,000 payments from Acme move forward following vote", "us"),
        item("Acme $5,000 payment plan advances after lawmakers vote", "us"),
        item("Wildfire forces evacuations in California", "us"),
    ]
    clusters = sorted((len(c) for c in vf.cluster_indices(stories)), reverse=True)
    assert clusters[0] >= 3 and clusters[-1] == 1, f"unexpected cluster sizes: {clusters}"

    print("verify_feed regression tests passed")


if __name__ == "__main__":
    main()
