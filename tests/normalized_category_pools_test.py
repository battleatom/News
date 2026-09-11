#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_news_normalized as normalized


def item(category, i, hours=1, source=None, state=""):
    published = datetime.now(timezone.utc) - timedelta(hours=hours)
    return {
        "title": f"Distinct {category} story number {i}",
        "description": f"Independent report {i}",
        "link": f"https://example.com/{category}/{i}",
        "pubDate": published.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "published": published,
        "source": source or f"Publisher {i % 12}",
        "category": category,
        "state": state,
    }


def test_policy():
    for category, policy in normalized.POOL_POLICY.items():
        if category == "local":
            assert policy == (20, 25, 30)
        else:
            assert policy == (30, 35, 40), (category, policy)
    assert normalized.core.MAX_AGE_HOURS == 96
    assert "when%3A4d" in normalized.core.feed_url("US news")


def test_normal_category_target():
    stories = [item("us", i, hours=i / 2) for i in range(60)]
    chosen = normalized.normalized_select_category(stories)
    assert len(chosen) == 35, len(chosen)


def test_local_target():
    stories = []
    for i in range(40):
        story = item("local", i, source=f"Local Publisher {i}")
        story["description"] += " Farmington New Mexico"
        stories.append(story)
    chosen = normalized.normalized_select_category(stories, limit=30)
    assert len(chosen) == 25, len(chosen)


def test_region_hard_cap_and_balance():
    normalized._region_total = 0
    total = []
    for bucket in range(8):
        stories = [item("region", bucket * 20 + i, state=f"State {bucket}-{i % 2}") for i in range(20)]
        chosen = normalized.normalized_select_region(stories, per_state=8, limit=80)
        assert len(chosen) <= 5
        total.extend(chosen)
    assert len(total) == 40, len(total)
    extra = normalized.normalized_select_region([item("region", 999, state="Extra")])
    assert extra == []


def test_previously_unprotected_fallbacks():
    for category in ("world", "us", "nm", "military"):
        assert category in normalized.core.TRUSTED_CATEGORY_FALLBACKS
        assert normalized.core.CATEGORY_POOL_MINIMUMS[category] == 30


if __name__ == "__main__":
    test_policy()
    test_normal_category_target()
    test_local_target()
    test_region_hard_cap_and_balance()
    test_previously_unprotected_fallbacks()
    print("Normalized category pool tests passed.")
