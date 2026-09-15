#!/usr/bin/env python3
"""V5.2 experimental collector wrapper.

V5.2 is intentionally additive: production V5.1 remains untouched.
Changes in this wrapper:
- expand normal Google News discovery and age acceptance to 14 days;
- use a larger ranked primary-source roster for Top Stories;
- rank Top Stories with source quality as a modest quality signal;
- rotate Top Stories by publisher round: every source's best distinct event first,
  then every source's second-best, then third-best (maximum 3/source);
- keep the existing event clustering/related-coverage logic from V5.1.

Google News remains the RSS discovery/transport layer. Publisher-specific queries,
source ranking, event clustering and diversity decide what is actually selected.
"""
from __future__ import annotations

import re
import urllib.parse
from collections import Counter, defaultdict

import update_news_v4 as v4

core = v4.core

V52_MAX_AGE_HOURS = 14 * 24
TOP_VISIBLE_WINDOW = 10
TOP_POOL_SIZE = 60
TOP_POOL_SOURCE_CAP = 3

# Additional strong publishers used as source-specific primary discovery for Top.
# These augment the V5.1 roster; they do not replace it.
V52_TOP_SOURCE_QUERIES = [
    ("Bloomberg", "site:bloomberg.com breaking world US politics economy news"),
    ("CNBC", "site:cnbc.com breaking US world politics economy news"),
    ("Politico", "site:politico.com breaking US politics government news"),
    ("The Hill", "site:thehill.com breaking US politics government news"),
    ("Axios", "site:axios.com breaking US politics world business news"),
    ("The Guardian", "site:theguardian.com breaking world US politics news"),
    ("PBS NewsHour", "site:pbs.org/newshour breaking US world politics news"),
    ("Al Jazeera", "site:aljazeera.com breaking world international US news"),
    ("Financial Times", "site:ft.com world US politics economy breaking news"),
    ("TIME", "site:time.com US world politics breaking news"),
]

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
    "pbsnewshour": 17,
    # Tier B — established national/international reporting
    "bloomberg": 17,
    "newyorktimes": 16,
    "washingtonpost": 16,
    "financialtimes": 16,
    "nbcnews": 15,
    "abcnews": 15,
    "cbsnews": 15,
    "cnbc": 15,
    "axios": 15,
    "politico": 14,
    "cnn": 14,
    "foxnews": 14,
    "aljazeera": 14,
    "usatoday": 13,
    "guardian": 13,
    "thehill": 12,
    "time": 12,
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


def rank_top_pool_v52(base_pool: list[dict]) -> list[dict]:
    """Round-robin an already event-clustered V5.1 Top pool by publisher.

    Round 1 = each publisher's highest-ranked distinct event.
    Round 2 = each publisher's second-highest distinct event.
    Round 3 = each publisher's third-highest distinct event.
    Within each round, stories are still ordered by impact/confirmation/source score.
    """
    if not base_pool:
        return []
    newest_time = max(x["published"] for x in base_pool)
    ranked = sorted(base_pool, key=lambda x: top_score(x, newest_time), reverse=True)

    buckets: dict[str, list[dict]] = defaultdict(list)
    seen_keys: set = set()
    for item in ranked:
        k = core.key(item)
        if not k or k in seen_keys:
            continue
        seen_keys.add(k)
        buckets[source_id(item.get("source") or "")].append(item)

    selected: list[dict] = []
    for round_index in range(TOP_POOL_SOURCE_CAP):
        round_items = [bucket[round_index] for bucket in buckets.values() if len(bucket) > round_index]
        round_items.sort(key=lambda x: top_score(x, newest_time), reverse=True)
        for item in round_items:
            if len(selected) >= TOP_POOL_SIZE:
                return selected
            selected.append(item)
    return selected


_original_select_top = core.select_top_stories


def select_top_stories_v52(unique):
    # Preserve V5.1 event clustering, duplicate handling, related links and impact
    # candidate selection, then apply V5.2 source-quality/diversity ordering.
    base = _original_select_top(unique)
    selected = rank_top_pool_v52(base)
    counts = Counter(source_id(x.get("source") or "") for x in selected)
    first10 = [source_id(x.get("source") or "") for x in selected[:10]]
    all_sources = {source_id(x.get("source") or "") for x in selected}
    first_round = [source_id(x.get("source") or "") for x in selected[:len(all_sources)]]
    print(
        "V5.2 TOP diversity: "
        f"{len(set(first10))}/{len(first10)} distinct sources in first 10; "
        f"{len(set(first_round))}/{len(first_round)} distinct in source round 1; "
        f"max source count {max(counts.values(), default=0)} across {len(selected)} retained stories."
    )
    return selected


# Augment the current V5.1 source roster without duplicating named publishers.
_existing_top_sources = {name.lower() for name, _ in core.MAINSTREAM_TOP_QUERIES}
for _name, _query in V52_TOP_SOURCE_QUERIES:
    if _name.lower() not in _existing_top_sources:
        core.MAINSTREAM_TOP_QUERIES.append((_name, _query))
        _existing_top_sources.add(_name.lower())

# Apply V5.2 behavior to the same core module used by the current V4/V5.1 chain.
core.MAX_AGE_HOURS = V52_MAX_AGE_HOURS
core.feed_url = expanded_feed_url
core.select_top_stories = select_top_stories_v52


def main():
    v4.main()


if __name__ == "__main__":
    main()
