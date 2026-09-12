#!/usr/bin/env python3
"""Fail closed when a generated V4 feed is not safe to promote.

This gate checks the generated RSS/site artifacts only. Browser behavior is covered by
Playwright tests in the stable-candidate workflow.
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
    "us": 15,
    "presidential": 15,
    "federal": 5,
    "legislation": 10,
    "nm": 15,
    "local": 40,
    "region": 15,
    "technology": 8,
    "gaming": 10,
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
ADULT_LABELS = {"ADULT INDUSTRY", "ADULT BUSINESS/LEGAL", "CREATOR", "ADULT AWARDS"}


def text(node: ET.Element, tag: str) -> str:
    return (node.findtext(tag) or "").strip()


def fail(message: str) -> None:
    raise SystemExit(f"V4 RELEASE GATE FAILED: {message}")


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
    clean = [i for i in entertainment if text(i, "entertainmentSafety") == "clean"]
    dirty = [i for i in entertainment if text(i, "entertainmentSafety") == "dirty"]
    adult = [i for i in dirty if text(i, "entertainmentLabel") in ADULT_LABELS]
    if len(clean) < 10:
        fail(f"Clean Entertainment has {len(clean)} stories; minimum is 10")
    if len(dirty) < 10:
        fail(f"Dirty Entertainment has {len(dirty)} stories; minimum is 10")
    if len(adult) < 5:
        fail(f"adult-industry Dirty pool has {len(adult)} stories; minimum is 5")
    if len(clean) + len(dirty) != len(entertainment):
        fail("Entertainment contains unclassified or overlapping safety records")
    for i in entertainment:
        if not text(i, "entertainmentLabel") or not text(i, "entertainmentScore"):
            fail(f"Entertainment ranking metadata missing for: {text(i, 'title')}")

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
        fail("Entertainment V4 UI must be injected exactly once")
    if "assets/location-content-v25.js" not in html:
        fail("location content controller is missing from generated site")

    print("V4 RELEASE GATE PASSED")
    print("Feed items:", len(items))
    print("Category counts:", dict(sorted(counts.items())))
    print("Entertainment: clean", len(clean), "dirty", len(dirty), "adult", len(adult))
    print("X topics:", x_topics)


if __name__ == "__main__":
    main()
