#!/usr/bin/env python3
"""Normalized production collector wrapper.

Keeps the stable collector intact while applying one consistent pool policy:
- ordinary tabs: minimum 30, target 35, hard max 40
- Local: minimum 20, target 25, hard max 30
- Region: one 40-story tab pool, balanced across its eight region buckets
- collection window: up to four days so quiet tabs can backfill with older stories
  while selectors continue to sort newest first.

X Top Issues and Underreported are intentionally outside this policy.
"""
from __future__ import annotations

import urllib.parse

import update_news as core

POOL_POLICY = {
    "world": (30, 35, 40),
    "us": (30, 35, 40),
    "presidential": (30, 35, 40),
    "federal": (30, 35, 40),
    "legislation": (30, 35, 40),
    "nm": (30, 35, 40),
    "region": (30, 35, 40),
    "nfl": (30, 35, 40),
    "technology": (30, 35, 40),
    "gaming": (30, 35, 40),
    "military": (30, 35, 40),
    "local": (20, 25, 30),
}

# Four-day ceiling. Selection remains newest-first, so older material only fills
# space after newer qualifying stories.
core.MAX_AGE_HOURS = 96
core.CATEGORY_POOL_MINIMUMS = {cat: policy[0] for cat, policy in POOL_POLICY.items()}


def expanded_feed_url(query):
    q = urllib.parse.quote(f"{query} when:4d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


core.feed_url = expanded_feed_url

# Give previously unprotected categories trusted replenishment sources. Existing
# source allowlisting and parsing rules still apply to every returned article.
core.TRUSTED_CATEGORY_FALLBACKS.update({
    "world": [
        ("Reuters", "site:reuters.com world international breaking news"),
        ("Associated Press", "site:apnews.com world international breaking news"),
        ("BBC", "site:bbc.com/news world international"),
        ("NPR", "site:npr.org world international"),
    ],
    "us": [
        ("Reuters", "site:reuters.com United States US politics national news"),
        ("Associated Press", "site:apnews.com United States US politics national news"),
        ("NPR", "site:npr.org United States national politics"),
        ("USA Today", "site:usatoday.com United States national news"),
    ],
    "nm": [
        ("Source New Mexico", "site:sourcenm.com New Mexico news government health education environment"),
        ("New Mexico In Depth", "site:nmindepth.com New Mexico news government education health"),
        ("Albuquerque Journal", "site:abqjournal.com New Mexico news"),
        ("Santa Fe New Mexican", "site:santafenewmexican.com New Mexico news"),
    ],
    "military": [
        ("Defense News", "site:defensenews.com Pentagon US military defense"),
        ("Military Times", "site:militarytimes.com US military Pentagon troops"),
        ("Breaking Defense", "site:breakingdefense.com Pentagon military defense"),
        ("Stars and Stripes", "site:stripes.com US military troops Pentagon"),
        ("Reuters", "site:reuters.com US military Pentagon defense"),
    ],
})

_original_select_category = core.select_category_stories
_original_select_region = core.select_region_stories
_region_total = 0


def normalized_select_category(items, limit=None):
    category = items[0].get("category") if items else ""
    _minimum, target, hard_max = POOL_POLICY.get(category, (30, 35, 40))
    requested = target if limit is None else min(int(limit), hard_max)
    # Explicit Local calls from the stable collector request 30 while our target
    # is 25; keep Local intentionally smaller unless a caller asks for less.
    if category == "local":
        requested = min(requested, target)
    return _original_select_category(items, limit=requested)


def normalized_select_region(items, per_state=8, limit=80):
    """Balance one 40-story Region pool across the eight collector buckets."""
    global _region_total
    hard_max = POOL_POLICY["region"][2]
    remaining = max(0, hard_max - _region_total)
    if not items or remaining == 0:
        return []
    # core.main invokes this once for each of eight named region buckets.
    bucket_cap = min(5, remaining)
    chosen = _original_select_region(items, per_state=per_state, limit=bucket_cap)
    _region_total += len(chosen)
    return chosen


core.select_category_stories = normalized_select_category
core.select_region_stories = normalized_select_region


def main():
    global _region_total
    _region_total = 0
    core.main()


if __name__ == "__main__":
    main()
