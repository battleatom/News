import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta, timezone

NEWS_FILE = Path("News")
STATS_FILE = Path("update-stats.json")

# Healthy means the category has enough usable stories for its intended UI.
# Counts above targetMax are useful depth, not a failure. These targets reflect
# the current V3 collectors after quality filters and regional expansion.
CATEGORY_TARGETS = {
    "top": (50, 60),
    "nfl": (20, 30),
    "x": (8, 15),
    "underreported": (25, 35),
    "world": (25, 45),
    "us": (15, 30),
    "presidential": (20, 30),
    "federal": (10, 30),
    "legislation": (15, 35),
    "nm": (20, 35),
    "local": (20, 35),
    "region": (100, 500),
    "technology": (20, 35),
    "gaming": (12, 25),
    "military": (5, 20),
    "boxoffice": (15, 30),
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
    ready = 0
    above_target = 0
    for category, (minimum, maximum) in CATEGORY_TARGETS.items():
        count = int(category_counts.get(category, 0))
        if count < minimum:
            state = "low"
            depth = "below-minimum"
        else:
            state = "healthy"
            ready += 1
            if count > maximum:
                depth = "above-target"
                above_target += 1
            else:
                depth = "target"
        health[category] = {
            "count": count,
            "targetMin": minimum,
            "targetMax": maximum,
            "status": state,
            "depth": depth,
        }
    for category, count in sorted(category_counts.items()):
        if category not in health:
            health[category] = {
                "count": int(count),
                "targetMin": None,
                "targetMax": None,
                "status": "untracked",
                "depth": "untracked",
            }
    return health, ready, above_target


def first_seen_map(links, previous_links, old, now_dt):
    """Keep when each currently served link first appeared on Underreported.

    Older stats files did not record this field. Existing legacy links are seeded
    four hours in the past so deploying this feature does not falsely mark the
    entire existing feed as NEW. Truly new links receive the current pull time.
    """
    prior = old.get("firstSeenAt", {}) if isinstance(old.get("firstSeenAt", {}), dict) else {}
    legacy_time = (now_dt - timedelta(hours=4)).isoformat()
    now_text = now_dt.isoformat()
    out = {}
    for link in links:
        value = clean(prior.get(link, ""))
        if value:
            out[link] = value
        elif link in previous_links:
            out[link] = legacy_time
        else:
            out[link] = now_text
    return out


def main():
    finalize = "--finalize" in sys.argv
    if not NEWS_FILE.exists():
        raise SystemExit("News feed not found")

    items, links, category_counts = feed_snapshot()
    health, ready_count, above_target_count = category_health(category_counts)
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    old = {}
    if STATS_FILE.exists():
        try:
            old = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    health_summary = {
        "healthy": ready_count,
        "ready": ready_count,
        "tracked": len(CATEGORY_TARGETS),
        "low": sum(1 for value in health.values() if value["status"] == "low"),
        "aboveTarget": above_target_count,
    }

    if not finalize:
        previous_links = set(old.get("currentLinks", []))
        new_links = [link for link in links if link not in previous_links] if previous_links else list(links)
        new_count = len(new_links)
        seen_at = first_seen_map(links, previous_links, old, now_dt)
        stats = {
            "updatedAt": now,
            "fetchedCount": len(items),
            "newCount": new_count,
            "newLinks": new_links,
            "firstSeenAt": seen_at,
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
        print(f"Pull stats recorded: {len(items)} fetched, {new_count} new before dedupe; {ready_count}/{len(CATEGORY_TARGETS)} category pools ready.")
        return

    stats = old or {}
    before = int(stats.get("fetchedCount", len(items)))
    final_link_set = set(links)
    surviving_new_links = [link for link in stats.get("newLinks", []) if link in final_link_set]
    prior_seen = stats.get("firstSeenAt", {}) if isinstance(stats.get("firstSeenAt", {}), dict) else {}
    final_seen = {link: prior_seen.get(link, now) for link in links}
    stats.update({
        "updatedAt": now,
        "fetchedCount": before,
        "newLinks": surviving_new_links,
        "firstSeenAt": final_seen,
        "duplicatesRemoved": max(0, before - len(items)),
        "finalCount": len(items),
        "categoryCounts": dict(sorted(category_counts.items())),
        "categoryHealth": health,
        "categoryHealthSummary": health_summary,
        "currentLinks": links,
        "status": "complete"
    })
    STATS_FILE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Pull stats finalized: {before} fetched, {stats.get('newCount', 0)} new, {stats['duplicatesRemoved']} removed, {len(items)} final; {ready_count}/{len(CATEGORY_TARGETS)} category pools ready.")


if __name__ == "__main__":
    main()
