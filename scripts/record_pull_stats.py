import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

NEWS_FILE = Path("News")
STATS_FILE = Path("update-stats.json")

# Desired retained story pools. The page still displays 10 initially and Load More
# controls presentation; these ranges measure whether collection depth is healthy.
CATEGORY_TARGETS = {
    "top": (50, 60),
    "nfl": (20, 30),
    "x": (5, 10),
    "underreported": (10, 20),
    "world": (25, 30),
    "us": (25, 30),
    "presidential": (20, 25),
    "federal": (25, 30),
    "legislation": (25, 35),
    "nm": (20, 30),
    "local": (20, 30),
    "region": (20, 30),
    "technology": (25, 30),
    "gaming": (25, 30),
    "military": (25, 30),
    "boxoffice": (15, 25),
}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def feed_snapshot():
    tree = ET.parse(NEWS_FILE)
    items = tree.getroot().findall("./channel/item")
    links = []
    category_counts = Counter()
    for item in items:
        link = clean(item.findtext("link"))
        category = clean(item.findtext("category")) or "world"
        category_counts[category] += 1
        if link:
            links.append(link)
    return items, links, category_counts


def category_health(category_counts):
    health = {}
    within = 0
    for category, (minimum, maximum) in CATEGORY_TARGETS.items():
        count = int(category_counts.get(category, 0))
        if count < minimum:
            state = "low"
        elif count > maximum:
            state = "high"
        else:
            state = "healthy"
            within += 1
        health[category] = {
            "count": count,
            "targetMin": minimum,
            "targetMax": maximum,
            "status": state,
        }
    # Preserve visibility into any future/unregistered categories instead of
    # silently dropping them from diagnostics.
    for category, count in sorted(category_counts.items()):
        if category not in health:
            health[category] = {
                "count": int(count),
                "targetMin": None,
                "targetMax": None,
                "status": "untracked",
            }
    return health, within


def main():
    finalize = "--finalize" in sys.argv
    if not NEWS_FILE.exists():
        raise SystemExit("News feed not found")

    items, links, category_counts = feed_snapshot()
    health, healthy_count = category_health(category_counts)
    now = datetime.now(timezone.utc).isoformat()
    old = {}
    if STATS_FILE.exists():
        try:
            old = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    health_summary = {
        "healthy": healthy_count,
        "tracked": len(CATEGORY_TARGETS),
        "low": sum(1 for value in health.values() if value["status"] == "low"),
        "high": sum(1 for value in health.values() if value["status"] == "high"),
    }

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
            "categoryCounts": dict(sorted(category_counts.items())),
            "categoryHealth": health,
            "categoryHealthSummary": health_summary,
            "currentLinks": links,
            "status": "pre-dedupe"
        }
        STATS_FILE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
        print(f"Pull stats recorded: {len(items)} fetched, {new_count} new before dedupe; {healthy_count}/{len(CATEGORY_TARGETS)} category pools healthy.")
        return

    stats = old or {}
    before = int(stats.get("fetchedCount", len(items)))
    stats.update({
        "updatedAt": now,
        "fetchedCount": before,
        "duplicatesRemoved": max(0, before - len(items)),
        "finalCount": len(items),
        "categoryCounts": dict(sorted(category_counts.items())),
        "categoryHealth": health,
        "categoryHealthSummary": health_summary,
        "currentLinks": links,
        "status": "complete"
    })
    STATS_FILE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Pull stats finalized: {before} fetched, {stats.get('newCount', 0)} new, {stats['duplicatesRemoved']} removed, {len(items)} final; {healthy_count}/{len(CATEGORY_TARGETS)} category pools healthy.")


if __name__ == "__main__":
    main()
