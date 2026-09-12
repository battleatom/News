from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import underreported_priority as under


def make_item(title, *, description="", source="Example", age_days=1, supporting=0, under_score=70, background="", what_next="", link="https://example.com/a"):
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = link
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "source").text = source
    ET.SubElement(item, "category").text = "underreported"
    ET.SubElement(item, "pubDate").text = format_datetime(datetime.now(timezone.utc) - timedelta(days=age_days))
    ET.SubElement(item, "supportingSourceCount").text = str(supporting)
    ET.SubElement(item, "underreportedScore").text = str(under_score)
    if background:
        ET.SubElement(item, "background").text = background
    if what_next:
        ET.SubElement(item, "whatNext").text = what_next
    return item


def add_pool(item, entries):
    pool = ET.SubElement(item, "coveragePool")
    now = datetime.now(timezone.utc)
    for idx, (source, age_hours, title) in enumerate(entries):
        article = ET.SubElement(pool, "article")
        ET.SubElement(article, "title").text = title
        ET.SubElement(article, "link").text = f"https://example.com/{source}/{idx}"
        ET.SubElement(article, "source").text = source
        ET.SubElement(article, "pubDate").text = format_datetime(now - timedelta(hours=age_hours))
    item.find("supportingSourceCount").text = str(len({source for source, _, _ in entries}))


def test_eligibility():
    assert not under.underreported_eligible(make_item("Hyrule Warriors Definitive Edition announced for Switch 2", source="Nintendo Life"))
    assert not under.underreported_eligible(make_item("Best gaming laptop deal drops Alienware price", source="PC Gamer"))
    assert under.underreported_eligible(make_item(
        "Steam age verification raises privacy and regulation concerns",
        description="Lawmakers and privacy advocates question the verification system.",
        source="Tom's Hardware",
    ))


def test_age_bands_and_freshness():
    now = datetime.now(timezone.utc)
    cases = [(1, "blue"), (3, "green"), (6, "orange"), (9, "purple"), (12, "red")]
    for days, expected in cases:
        assert under.age_band(now - timedelta(days=days), now) == expected
    assert under.freshness_score(now - timedelta(hours=12), now) > under.freshness_score(now - timedelta(days=4), now)


def test_corroboration_coverage_gap_and_saturation():
    assert under.corroboration_score(make_item("A", supporting=0)) == 15
    assert under.corroboration_score(make_item("A", supporting=1)) == 40
    assert under.corroboration_score(make_item("A", supporting=3)) == 80
    assert under.corroboration_score(make_item("A", supporting=5)) == 100
    assert under.coverage_gap_score(make_item("A", supporting=2)) > under.coverage_gap_score(make_item("A", supporting=10))
    assert under.saturation_penalty(make_item("A", supporting=5)) == 0
    assert under.saturation_penalty(make_item("A", supporting=12)) == 10


def test_momentum_rewards_accelerating_coverage():
    rising = make_item(
        "Investigation expands after water contamination found",
        description="Government investigation examines pollution, water and public health.",
    )
    add_pool(rising, [
        ("Reuters", 2, "Water contamination investigation expands"),
        ("Associated Press", 4, "Officials investigate contaminated water"),
        ("NPR", 10, "More testing ordered for contamination"),
        ("BBC", 30, "Earlier contamination report"),
    ])
    stagnant = make_item(
        "Investigation expands after water contamination found",
        description="Government investigation examines pollution, water and public health.",
    )
    add_pool(stagnant, [
        ("Reuters", 20, "Water contamination investigation expands"),
        ("Associated Press", 40, "Officials investigate contaminated water"),
        ("NPR", 50, "More testing ordered for contamination"),
        ("BBC", 60, "Earlier contamination report"),
    ])
    now = datetime.now(timezone.utc)
    assert under.momentum_score(rising, now) > under.momentum_score(stagnant, now)


def test_freshness_changes_ranking_for_similar_events():
    now = datetime.now(timezone.utc)
    fresh = make_item(
        "Investigation finds pollution in public water system",
        description="Government investigation examines pollution, public health and water safety.",
        age_days=0.5,
        supporting=3,
    )
    old = make_item(
        "Investigation finds pollution in public water system",
        description="Government investigation examines pollution, public health and water safety.",
        age_days=5,
        supporting=3,
        link="https://example.com/b",
    )
    add_pool(fresh, [("Reuters", 4, "Water system investigation"), ("AP", 10, "Pollution found in public water"), ("NPR", 18, "Officials order tests")])
    add_pool(old, [("Reuters", 100, "Water system investigation"), ("AP", 110, "Pollution found in public water"), ("NPR", 120, "Officials order tests")])
    fresh_scores = under.ranking_components(fresh, under.parse_date(fresh.findtext("pubDate")), now)
    old_scores = under.ranking_components(old, under.parse_date(old.findtext("pubDate")), now)
    assert fresh_scores["priority"] > old_scores["priority"], (fresh_scores, old_scores)


def test_event_level_clustering_unifies_duplicate_headlines():
    now = datetime.now(timezone.utc)
    first = make_item(
        "EPA investigation expands after toxic groundwater contamination",
        description="Government investigation examines pollution, water and public health.",
        supporting=2,
        link="https://example.com/main-a",
    )
    second = make_item(
        "Toxic groundwater contamination prompts expanded EPA investigation",
        description="Government investigation examines pollution, water and public health.",
        supporting=2,
        link="https://example.com/main-b",
    )
    add_pool(first, [("Reuters", 4, "EPA expands groundwater contamination investigation"), ("AP", 8, "Groundwater contamination investigation grows")])
    add_pool(second, [("Reuters", 4, "EPA expands groundwater contamination investigation"), ("NPR", 9, "Residents warned over contaminated groundwater")])
    merged, collapsed = under.cluster_underreported_events([first, second], now)
    assert collapsed == 1
    assert len(merged) == 1
    assert under.supporting_source_count(merged[0]) >= 3


def test_live_feed_copy():
    with tempfile.TemporaryDirectory() as td:
        test_news = Path(td) / "News"
        tree = ET.parse(ROOT / "News")
        tree.write(test_news, encoding="utf-8", xml_declaration=True)
        original = under.NEWS
        try:
            under.NEWS = test_news
            under.rank()
        finally:
            under.NEWS = original

        items = ET.parse(test_news).getroot().findall("./channel/item")
        under_items = [x for x in items if (x.findtext("category") or "").strip().lower() == "underreported"]
        assert len(under_items) <= under.MAX_ITEMS
        assert all(under.underreported_eligible(x) for x in under_items)
        assert all((x.findtext("ageBand") or "") in {"blue", "green", "orange", "purple", "red"} for x in under_items)
        assert all(x.find("corroborationScore") is not None for x in under_items)
        assert all(x.find("coverageGapScore") is not None for x in under_items)
        assert all(x.find("coverageMomentumScore") is not None for x in under_items)
        assert all(x.find("continuingRelevanceScore") is not None for x in under_items)
        bad_fragments = ("definitive edition", "gaming laptop deal", "videos for pc")
        titles = [(x.findtext("title") or "").lower() for x in under_items]
        assert not any(fragment in title for title in titles for fragment in bad_fragments)
        print(f"Validated {len(under_items)} event-ranked Underreported stories on a live-feed copy.")


if __name__ == "__main__":
    test_eligibility()
    test_age_bands_and_freshness()
    test_corroboration_coverage_gap_and_saturation()
    test_momentum_rewards_accelerating_coverage()
    test_freshness_changes_ranking_for_similar_events()
    test_event_level_clustering_unifies_duplicate_headlines()
    test_live_feed_copy()
    print("UNDERREPORTED PRIORITY TEST PASS")
