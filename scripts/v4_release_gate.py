#!/usr/bin/env python3
"""Fail closed when a generated V5 feed is not safe to promote.

This gate checks generated RSS/site artifacts only. Browser behavior is covered by
Playwright smoke tests. Volume floors are intentionally conservative because the V5
authoritative filters prioritize category precision over retaining weakly qualified
stories; semantic relevance, duplicate, routing, X-topic, Box Office, and structural
quality are enforced by separate gates earlier in the production workflow.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "News"
INDEX = ROOT / "index.html"
VERIFY = ROOT / "verification-report.json"

MIN_COUNTS = {
    "top": 20,
    "nfl": 10,
    "underreported": 20,
    "world": 15,
    "us": 5,
    "presidential": 15,
    "federal": 5,
    "legislation": 10,
    "nm": 15,
    "local": 1,
    "region": 5,
    "technology": 5,
    "gaming": 5,
    "military": 15,
}
EXPECTED_X = [
    "Health",
    "Technology & AI",
    "Celebrities & Public Figures",
    "World",
    "Politics & Government",
    "Entertainment",
    "Sports",
    "Business & Economy",
    "Gaming",
    "Science",
]


def text(node: ET.Element, tag: str) -> str:
    return (node.findtext(tag) or "").strip()


def fail(message: str) -> None:
    raise SystemExit(f"V5 RELEASE GATE FAILED: {message}")


def main() -> None:
    if not NEWS.exists() or not INDEX.exists():
        fail("generated News/index.html artifacts are missing")

    root = ET.parse(NEWS).getroot()
    items = root.findall(".//item")
    if not items:
        fail("feed contains zero items")

    counts = Counter(text(i, "category") for i in items)
    for category, minimum in MIN_COUNTS.items():
        if counts.get(category, 0) < minimum:
            fail(f"{category} has {counts.get(category, 0)} stories; minimum is {minimum}")

    malformed = []
    for i in items:
        if not text(i, "title") or not text(i, "link") or not text(i, "category"):
            malformed.append(text(i, "title") or "<untitled>")
    if malformed:
        fail(f"{len(malformed)} malformed item(s) lack title/link/category")

    entertainment = [i for i in items if text(i, "category") == "entertainment"]
    dirty = [i for i in entertainment if text(i, "entertainmentSafety").lower() == "dirty"]
    if dirty:
        fail(f"Dirty Entertainment is disabled but {len(dirty)} dirty record(s) remain")

    x_items = [i for i in items if text(i, "category") == "x"]
    x_topics = [text(i, "xTopic") for i in x_items]
    if x_topics != EXPECTED_X:
        fail(f"X topics are not the fixed ten-topic sequence: {x_topics}")

    legislation = [i for i in items if text(i, "category") == "legislation"]
    if any(not text(i, "link") for i in legislation):
        fail("Legislation contains a record without an official link")

    if VERIFY.exists():
        report = json.loads(VERIFY.read_text(encoding="utf-8"))
        residual = report.get("residualStrongDuplicatePairs", [])
        if residual:
            fail(f"verification report contains {len(residual)} residual strong duplicate pair(s)")

    html = INDEX.read_text(encoding="utf-8")
    if html.count("assets/entertainment-v4.js") != 1:
        fail("Entertainment UI must be injected exactly once")
    if "assets/location-content-v25.js" not in html:
        fail("location content controller is missing from generated site")

    print("V5 RELEASE GATE PASSED")
    print("Feed items:", len(items))
    print("Category counts:", dict(sorted(counts.items())))
    print("Entertainment dirty records:", len(dirty))
    print("X topics:", x_topics)


if __name__ == "__main__":
    main()
