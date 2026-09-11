#!/usr/bin/env python3
"""Verify that GitHub Pages is serving the exact freshly generated build."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://battleatom.github.io/News/"
ATTEMPTS = 15
DELAY = 20


def fetch(path: str) -> bytes:
    stamp = str(int(time.time() * 1000))
    url = urllib.parse.urljoin(BASE, path) + f"?v={stamp}"
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "NewsLiveSmoke/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned HTTP {response.status}")
        return response.read()


def main() -> None:
    local_health = json.loads(Path("refresh-health.json").read_text(encoding="utf-8"))
    expected = local_health.get("generatedAt")
    if not expected or local_health.get("status") != "healthy":
        raise SystemExit("Local build is not healthy; refusing deployed-site verification")

    remote_health = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            remote_health = json.loads(fetch("refresh-health.json").decode("utf-8"))
            if remote_health.get("status") == "healthy" and remote_health.get("generatedAt") == expected:
                break
            print(f"Pages not current yet ({attempt}/{ATTEMPTS}); remote={remote_health.get('generatedAt')} expected={expected}")
        except Exception as exc:
            print(f"Pages check failed ({attempt}/{ATTEMPTS}): {exc}")
        if attempt < ATTEMPTS:
            time.sleep(DELAY)
    else:
        raise SystemExit("GitHub Pages did not publish the current validated build within the verification window")

    index = fetch("index.html").decode("utf-8", "replace")
    if "UNDERREPORTED" not in index or "News" not in index:
        raise SystemExit("Live index.html is missing expected application markers")

    feed = ET.fromstring(fetch("News"))
    items = feed.findall(".//item")
    if len(items) < 25:
        raise SystemExit(f"Live News feed is unexpectedly small: {len(items)} items")

    categories = {(item.findtext("category") or "").strip().lower() for item in items}
    required = {"top", "us", "world", "technology", "gaming"}
    missing = required - categories
    if missing:
        raise SystemExit(f"Live News feed is missing expected categories: {sorted(missing)}")

    print(f"Live deployment verified: {len(items)} articles, health timestamp {expected}")


if __name__ == "__main__":
    main()
