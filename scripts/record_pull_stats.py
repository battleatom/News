import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

NEWS_FILE = Path("News")
STATS_FILE = Path("update-stats.json")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def feed_snapshot():
    tree = ET.parse(NEWS_FILE)
    items = tree.getroot().findall("./channel/item")
    links = []
    for item in items:
        link = clean(item.findtext("link"))
        if link:
            links.append(link)
    return items, links


def main():
    finalize = "--finalize" in sys.argv
    if not NEWS_FILE.exists():
        raise SystemExit("News feed not found")

    items, links = feed_snapshot()
    now = datetime.now(timezone.utc).isoformat()
    old = {}
    if STATS_FILE.exists():
        try:
            old = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    if not finalize:
        previous_links = set(old.get("currentLinks", []))
        new_count = sum(1 for link in links if link not in previous_links) if previous_links else len(links)
        stats = {
            "updatedAt": now,
            "fetchedCount": len(items),
            "newCount": new_count,
            "duplicatesRemoved": 0,
            "languageFiltered": 0,
            "finalCount": len(items),
            "currentLinks": links,
            "status": "pre-dedupe"
        }
        STATS_FILE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
        print(f"Pull stats recorded: {len(items)} fetched, {new_count} new before dedupe.")
        return

    stats = old or {}
    before = int(stats.get("fetchedCount", len(items)))
    stats.update({
        "updatedAt": now,
        "fetchedCount": before,
        "duplicatesRemoved": max(0, before - len(items)),
        "finalCount": len(items),
        "currentLinks": links,
        "status": "complete"
    })
    STATS_FILE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Pull stats finalized: {before} fetched, {stats.get('newCount', 0)} new, {stats['duplicatesRemoved']} removed, {len(items)} final.")


if __name__ == "__main__":
    main()
