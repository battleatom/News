from __future__ import annotations

from model import Story


def _key(story: Story) -> tuple[str, str]:
    return ((story.url or "").strip().lower(), (story.title or "").strip().lower())


def select_fixed_x_slots(processed: list[Story], raw: list[Story], registry: dict) -> list[Story]:
    """Replace generic X selection with one current lead per configured fixed X slot."""
    source_ids = [
        str(source.get("id", ""))
        for source in registry.get("sources", [])
        if source.get("category") == "x" and source.get("id")
    ]
    if not source_ids:
        return processed

    chosen: list[Story] = []
    used: set[tuple[str, str]] = set()
    for source_id in source_ids:
        candidates = [
            story for story in raw
            if story.category == "x" and story.source_id == source_id and story.title and story.url
        ]
        candidates.sort(key=lambda story: story.published_dt, reverse=True)
        pick = next((story for story in candidates if _key(story) not in used), None)
        if pick is None and candidates:
            pick = candidates[0]
        if pick is not None:
            used.add(_key(pick))
            chosen.append(pick)

    return [story for story in processed if story.category != "x"] + chosen
