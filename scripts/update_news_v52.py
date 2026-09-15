#!/usr/bin/env python3
"""V5.2 experimental collector wrapper.

V5.2 is intentionally additive: production V5.1 remains untouched.
Changes in this wrapper:
- expand normal Google News discovery and age acceptance to 14 days;
- rank Top Stories with source quality as a modest tie/quality signal;
- enforce source diversity: first 10 max 1/source, first 30 max 2/source,
  full 60 max 3/source;
- keep the existing event clustering/related-coverage logic from V5.1.
"""
from __future__ import annotations

import re
import urllib.parse
from collections import Counter

import update_news_v4 as v4

core = v4.core

V52_MAX_AGE_HOURS = 14 * 24
TOP_VISIBLE_WINDOW = 10
TOP_MID_WINDOW = 30
TOP_POOL_SIZE = 60
TOP_VISIBLE_SOURCE_CAP = 1
TOP_MID_SOURCE_CAP = 2
TOP_POOL_SOURCE_CAP = 3

# General-news source ranking. This is deliberately a modest ranking signal, not
# an editorial override: story impact, freshness and multi-source confirmation
# remain more important than publisher name alone.
SOURCE_QUALITY = {
    # Tier A — wire/public-service/strong international primary reporting
    "reuters": 20,
    "associatedpress": 20,
    "ap": 20,
    "afp": 19,
    "bbc": 18,
    "npr": 18,
    # Tier B — established national/international reporting
    "bloomberg": 17,
    "newyorktimes": 16,
    "washingtonpost": 16,
    "nbcnews": 15,
    "abcnews": 15,
    "cbsnews": 15,
    "cnn": 14,
    "foxnews": 14,
    "usatoday": 13,
    "theguardian": 13,
    "politico": 14,
    "thehill": 12,
    # Tier C — strong category specialists
    "espn": 14,
    "nflcom": 15,
    "theverge": 14,
    "arstechnica": 15,
    "techcrunch": 12,
    "wired": 13,
    "defensenews": 14,
    "militarytimes": 13,
    "breakingdefense": 14,
    "variety": 14,
    "hollywoodreporter": 14,
    "deadline": 13,
    "billboard": 13,
    # Tier D — regional/local public-interest reporting (not penalized for size)
    "sourcenewmexico": 15,
    "newmexicoindepth": 15,
    "tricityrecord": 14,
    "durangoherald": 13,
    "navajotimes": 14,
}


def source_id(value: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    if raw.startswith("the") and raw[3:] in SOURCE_QUALITY:
        raw = raw[3:]
    if raw.startswith("associatedpress"):
        return "associatedpress"
    if raw.startswith("reuters"):
        return "reuters"
    if raw.startswith("bbc"):
        return "bbc"
    return raw or "unknown"


def source_quality(item: dict) -> int:
    sid = source_id(item.get("source") or "")
    if sid in SOURCE_QUALITY:
        return SOURCE_QUALITY[sid]
    # Unknown but already-approved sources remain eligible; they simply do not
    # receive a quality bonus.
    return 8


def expanded_feed_url(query):
    q = urllib.parse.quote(f"{query} when:14d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _related_source_count(item: dict) -> int:
    sources = {source_id(item.get("source") or "")}
    for rel in item.get("_relatedArticles", []) or []:
        sources.add(source_id(rel.get("source") or ""))
    sources.discard("unknown")
    return max(1, len(sources))


def top_score(item: dict, newest_time) -> tuple:
    # V5.1 impact scoring already includes freshness and category signals.
    impact = core.impact_score(item, newest_time)
    confirmation = min(20, max(0, _related_source_count(item) - 1) * 5)
    quality = source_quality(item)
    return (impact + confirmation + quality, item.get("published"))


def _take_with_cap(ranked: list[dict], selected: list[dict], selected_keys: set, counts: Counter,
                   cap: int, stop_at: int) -> None:
    for item in ranked:
        if len(selected) >= stop_at:
            return
        k = core.key(item)
        sid = source_id(item.get("source") or "")
        if not k or k in selected_keys or counts[sid] >= cap:
            continue
        selected.append(item)
        selected_keys.add(k)
        counts[sid] += 1


def rank_top_pool_v52(base_pool: list[dict]) -> list[dict]:
    """Re-rank an already event-clustered V5.1 Top pool with source diversity."""
    if not base_pool:
        return []
    newest_time = max(x["published"] for x in base_pool)
    ranked = sorted(base_pool, key=lambda x: top_score(x, newest_time), reverse=True)

    selected: list[dict] = []
    selected_keys: set = set()
    counts: Counter = Counter()

    # Screen 1: one best distinct event per publisher.
    _take_with_cap(ranked, selected, selected_keys, counts, TOP_VISIBLE_SOURCE_CAP, TOP_VISIBLE_WINDOW)
    # If fewer than ten distinct publishers exist, allow a second item only as a fallback.
    if len(selected) < TOP_VISIBLE_WINDOW:
        _take_with_cap(ranked, selected, selected_keys, counts, TOP_MID_SOURCE_CAP, TOP_VISIBLE_WINDOW)

    # Deeper list: two per source through card 30.
    _take_with_cap(ranked, selected, selected_keys, counts, TOP_MID_SOURCE_CAP, TOP_MID_WINDOW)
    # Full rotation: at most three per publisher.
    _take_with_cap(ranked, selected, selected_keys, counts, TOP_POOL_SOURCE_CAP, TOP_POOL_SIZE)
    return selected


_original_select_top = core.select_top_stories


def select_top_stories_v52(unique):
    # Preserve V5.1 event clustering, duplicate handling, related links and impact
    # candidate selection, then apply V5.2 source-quality/diversity ordering.
    base = _original_select_top(unique)
    selected = rank_top_pool_v52(base)
    counts = Counter(source_id(x.get("source") or "") for x in selected)
    first10 = [source_id(x.get("source") or "") for x in selected[:10]]
    print(
        "V5.2 TOP diversity: "
        f"{len(set(first10))}/{len(first10)} distinct sources in first 10; "
        f"max source count {max(counts.values(), default=0)} across {len(selected)} retained stories."
    )
    return selected


# Apply V5.2 behavior to the same core module used by the current V4/V5.1 chain.
core.MAX_AGE_HOURS = V52_MAX_AGE_HOURS
core.feed_url = expanded_feed_url
core.select_top_stories = select_top_stories_v52


def main():
    v4.main()


if __name__ == "__main__":
    main()
