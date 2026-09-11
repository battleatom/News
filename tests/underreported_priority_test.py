from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import underreported_priority as under


def make_item(title, *, description="", source="Example", age_days=1, supporting=0, under_score=70, background="", what_next=""):
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
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


def test_eligibility():
    assert not under.underreported_eligible(make_item("Hyrule Warriors Definitive Edition announced for Switch 2", source="Nintendo Life"))
    assert not under.underreported_eligible(make_item("Best gaming laptop deal drops Alienware price", source="PC Gamer"))
    assert under.underreported_eligible(make_item(
        "Steam age verification raises privacy and regulation concerns",
        description="Lawmakers and privacy advocates question the verification system.",
        source="Tom's Hardware",
    ))


def test_age_bands():
    now = datetime.now(timezone.utc)
    cases = [(1, "blue"), (3, "green"), (6, "orange"), (9, "purple"), (12, "red")]
    for days, expected in cases:
        assert under.age_band(now - timedelta(days=days), now) == expected


def test_corroboration_and_ranking():
    assert under.corroboration_score(make_item("A", supporting=0)) == 20
    assert under.corroboration_score(make_item("A", supporting=1)) == 45
    assert under.corroboration_score(make_item("A", supporting=3)) == 80
    assert under.corroboration_score(make_item("A", supporting=5)) == 90

    now = datetime.now(timezone.utc)
    older_important = make_item(
        "Investigation finds wildfire pollution threatens public water systems",
        description="A continuing investigation examines pollution, public health and government response.",
        age_days=6,
        supporting=3,
        under_score=70,
        background="Earlier reporting documented the continuing wildfire and water risks.",
        what_next="A public hearing is scheduled next week.",
    )
    fresh_low_value = make_item(
        "Small lifestyle feature gets limited coverage",
        age_days=0.2,
        supporting=0,
        under_score=96,
    )
    old_scores = under.ranking_components(older_important, under.parse_date(older_important.findtext("pubDate")), now)
    new_scores = under.ranking_components(fresh_low_value, under.parse_date(fresh_low_value.findtext("pubDate")), now)
    assert old_scores["priority"] > new_scores["priority"], (old_scores, new_scores)


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
        assert all(x.find("continuingRelevanceScore") is not None for x in under_items)

        bad_fragments = ("definitive edition", "gaming laptop deal", "videos for pc")
        titles = [(x.findtext("title") or "").lower() for x in under_items]
        assert not any(fragment in title for title in titles for fragment in bad_fragments)
        print(f"Validated {len(under_items)} ranked Underreported stories on a live-feed copy.")


if __name__ == "__main__":
    test_eligibility()
    test_age_bands()
    test_corroboration_and_ranking()
    test_live_feed_copy()
    print("UNDERREPORTED PRIORITY TEST PASS")
