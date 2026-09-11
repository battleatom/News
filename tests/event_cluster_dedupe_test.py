import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dedupe_news_stories as event_dedupe


def item(title, category="us", description="", source="Example"):
    node = ET.Element("item")
    for tag, value in (
        ("title", title), ("description", description), ("source", source),
        ("category", category), ("link", "https://example.com/" + str(abs(hash(title)))),
    ):
        ET.SubElement(node, tag).text = value
    return node


def synthetic_regressions():
    a = item("Trump promises $5,000 payments to U.S. adults if GOP wins Congress - CBS News")
    b = item("$5,000 checks promised by Trump if Republicans keep House and Senate - NBC News")
    c = item("Trump says he does not regret Iran war despite midterm concerns - Reuters")
    d = item("White House announces new immigration enforcement rules at southern border - AP News")
    e = item("Trump backs tougher border deportation rules in new immigration push - CNN")
    f = item("Federal judge blocks unrelated immigration detention policy in California - NPR")

    assert event_dedupe.same_us_event(a, b), "Same $5,000 payment event was not clustered"
    assert not event_dedupe.same_us_event(a, c), "Unrelated Trump story was incorrectly clustered"
    assert not event_dedupe.same_us_event(d, f), "Different immigration events were incorrectly clustered"
    assert not event_dedupe.same_us_event(a, item("Trump proposes $5,000 gaming prize", category="technology")), "Cross-category stories must not cluster"

    # Regional sports regression: generic football/game/prediction language must not
    # merge unrelated matchups that happen to appear in the same regional feed.
    florida_miami = item(
        "Florida A&M vs Miami football prediction, odds and game preview",
        category="region",
    )
    michigan_oklahoma = item(
        "Michigan vs Oklahoma football prediction, odds and game preview",
        category="region",
    )
    assert not event_dedupe.legacy.same_story(
        florida_miami, michigan_oklahoma
    ), "Unrelated regional college football matchups were incorrectly clustered"

    # Genuine duplicate coverage of one regional sports event should still collapse
    # when two stable named anchors identify the same matchup.
    miami_a = item(
        "Miami Hurricanes vs Florida Gators football game preview and prediction",
        category="region",
    )
    miami_b = item(
        "Florida Gators at Miami Hurricanes: prediction and game preview",
        category="region",
    )
    assert event_dedupe.legacy.same_story(
        miami_a, miami_b
    ), "Same regional sports event was not clustered"


def live_feed_diagnostic():
    news = ROOT / "News"
    tree = ET.parse(news)
    items = tree.getroot().findall("./channel/item")
    us = [x for x in items if (x.findtext("category") or "").strip().lower() == "us"]
    pairs = []
    for i, left in enumerate(us):
        for right in us[i + 1:]:
            if event_dedupe.same_us_event(left, right):
                pairs.append((event_dedupe.legacy.title_without_source(left), event_dedupe.legacy.title_without_source(right)))

    print(f"Live U.S. articles before event pass: {len(us)}")
    print(f"Live same-event pairs detected: {len(pairs)}")
    for left, right in pairs[:20]:
        print("PAIR:", left, "||", right)

    with tempfile.TemporaryDirectory() as td:
        test_feed = Path(td) / "News"
        shutil.copy2(news, test_feed)
        removed = event_dedupe.event_dedupe_pass(str(test_feed), write_report=False)
        post = ET.parse(test_feed).getroot().findall("./channel/item")
        post_us = [x for x in post if (x.findtext("category") or "").strip().lower() == "us"]
        remaining_pairs = []
        for i, left in enumerate(post_us):
            for right in post_us[i + 1:]:
                if event_dedupe.same_us_event(left, right):
                    remaining_pairs.append((left.findtext("title"), right.findtext("title")))
        assert not remaining_pairs, f"Event duplicate pairs remain after pass: {remaining_pairs[:3]}"
        assert len(post_us) == len(us) - len(removed), "Unexpected U.S. article count after event pass"
        print(f"Live U.S. articles after event pass: {len(post_us)}")
        print(f"Live U.S. event duplicates removed: {len(removed)}")


if __name__ == "__main__":
    synthetic_regressions()
    live_feed_diagnostic()
    print("Event-cluster dedupe validation passed.")
