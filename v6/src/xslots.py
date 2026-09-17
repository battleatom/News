from __future__ import annotations

from model import Story


def _key(story: Story) -> tuple[str, str]:
    return ((story.url or "").strip().lower(), (story.title or "").strip().lower())


def select_fixed_x_slots(processed: list[Story], raw: list[Story], registry: dict) -> list[Story]:
    """Keep one active lead plus one backup candidate for each configured X slot."""
    source_ids = [
        str(source.get("id", ""))
        for source in registry.get("sources", [])
        if source.get("category") == "x" and source.get("id")
    ]
    if not source_ids:
        return processed

    leads: list[Story] = []
    backups: list[Story] = []
    used: set[tuple[str, str]] = set()

    for source_id in source_ids:
        candidates = [
            story for story in raw
            if story.category == "x" and story.source_id == source_id and story.title and story.url
        ]
        candidates.sort(key=lambda story: story.published_dt, reverse=True)

        picks: list[Story] = []
        for story in candidates:
            key = _key(story)
            if key in used:
                continue
            used.add(key)
            picks.append(story)
            if len(picks) == 2:
                break

        if picks:
            leads.append(picks[0])
        if len(picks) > 1:
            backups.append(picks[1])

    # Keep backups first and leads second. The X renderer selects the last surviving
    # candidate for each topic, so the lead is shown normally and the backup is
    # promoted immediately if feedback suppresses the lead in the browser.
    return [story for story in processed if story.category != "x"] + backups + leads
