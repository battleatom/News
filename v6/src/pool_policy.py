from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from model import Story

# Quiet local/state categories need longer retention because publishers post less often.
MAX_AGE_HOURS = {
    "top": 72,
    "world": 96,
    "us": 96,
    "presidential": 120,
    "federal": 120,
    "legislation": 168,
    "nm": 168,
    "local": 240,
    "region": 168,
    "technology": 96,
    "gaming": 120,
    "military": 120,
    "entertainment": 96,
    "underreported": 240,
    "nfl": 96,
    "x": 48,
}

# High-impact stories can outlive the normal window, but not indefinitely.
IMPORTANT_BONUS_HOURS = 72
IMPORTANT_THRESHOLD = 24.0
FRESH_SURGE_HOURS = 12


def _age_hours(story: Story, now: datetime) -> float:
    return max(0.0, (now - story.published_dt).total_seconds() / 3600)


def _keep(story: Story, now: datetime) -> bool:
    base = MAX_AGE_HOURS.get(story.category, 120)
    limit = base + (IMPORTANT_BONUS_HOURS if story.importance >= IMPORTANT_THRESHOLD else 0)
    return _age_hours(story, now) <= limit


def apply_rolling_pool(stories: list[Story], registry: dict, *, now: datetime | None = None) -> tuple[list[Story], dict]:
    """Retire stale/low-value inventory and let reserves expand during fresh-news surges.

    The configured visible_target is stable UI capacity. reserve_ratio is the normal reserve,
    while expansion_ratio is additional temporary capacity unlocked when fresh supply exists.
    The resulting pool is intentionally allowed to grow and contract between refreshes.
    """
    now = now or datetime.now(timezone.utc)
    grouped: dict[str, list[Story]] = defaultdict(list)
    retired: dict[str, int] = defaultdict(int)
    for story in stories:
        if _keep(story, now):
            grouped[story.category].append(story)
        else:
            retired[story.category] += 1

    output: list[Story] = []
    capacities: dict[str, dict] = {}
    for category, cfg in registry["categories"].items():
        rows = grouped.get(category, [])
        rows.sort(key=lambda s: (s.published_dt, s.importance), reverse=True)
        visible = int(cfg.get("visible_target", cfg.get("target", 50)))
        if category == "x":
            source_ids = [
                str(source.get("id", ""))
                for source in registry.get("sources", [])
                if source.get("category") == "x" and source.get("id")
            ]
            per_slot = {source_id: [] for source_id in source_ids}
            for story in rows:
                if story.source_id in per_slot:
                    per_slot[story.source_id].append(story)
            primaries = [per_slot[source_id][0] for source_id in source_ids if per_slot[source_id]]
            backups = [per_slot[source_id][1] for source_id in source_ids if len(per_slot[source_id]) > 1]
            rows = primaries + backups
        reserve_ratio = max(0.0, float(cfg.get("reserve_ratio", 0.20)))
        expansion_ratio = max(0.0, float(cfg.get("expansion_ratio", 0.30)))
        normal_reserve = round(visible * reserve_ratio)
        expansion = round(visible * expansion_ratio)
        fresh_count = sum(_age_hours(story, now) <= FRESH_SURGE_HOURS for story in rows)
        # Expansion is demand-driven: only fresh supply beyond the normal pool unlocks it.
        normal_capacity = visible + normal_reserve
        surge = max(0, fresh_count - visible)
        expansion_used = min(expansion, surge)
        capacity = normal_capacity + expansion_used
        kept = rows[:capacity]
        output.extend(kept)
        capacities[category] = {
            "visibleTarget": visible,
            "normalReserveTarget": normal_reserve,
            "expansionCapacity": expansion,
            "expansionUsed": expansion_used,
            "poolCapacity": capacity,
            "candidateCount": len(rows),
            "keptCount": len(kept),
            "retiredStaleCount": retired.get(category, 0),
        }

    order = {name: i for i, name in enumerate(registry["categories"])}
    output.sort(key=lambda s: (order.get(s.category, 999), -s.published_dt.timestamp()))
    return output, {"categories": capacities, "retiredStaleCount": sum(retired.values())}
