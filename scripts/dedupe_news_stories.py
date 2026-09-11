import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import dedupe_news_legacy as legacy

NEWS_FILE = "News"
REPORT_FILE = Path("event-dedupe-report.json")

US_EVENT_GROUPS = {
    "payments": {"payment", "payments", "check", "checks", "rebate", "rebates", "dividend", "dividends", "stimulus", "refund", "refunds", "bonus", "bonuses", "payout", "payouts", "cash", "promise", "promises", "promised"},
    "elections": {"election", "elections", "midterm", "midterms", "vote", "votes", "voting", "ballot", "ballots", "campaign", "campaigns"},
    "immigration": {"immigration", "immigrant", "immigrants", "migrant", "migrants", "border", "deportation", "deportations", "asylum", "visa", "visas"},
    "courts": {"court", "courts", "judge", "judges", "ruling", "rulings", "lawsuit", "lawsuits", "supreme", "appeal", "appeals"},
    "taxes": {"tax", "taxes", "tariff", "tariffs", "deduction", "deductions", "credit", "credits", "irs"},
    "health": {"health", "healthcare", "medicaid", "medicare", "insurance", "hospital", "hospitals"},
    "crime": {"shooting", "shootings", "murder", "murders", "crime", "crimes", "arrest", "arrests", "charged", "charges", "indictment"},
    "disaster": {"hurricane", "tornado", "tornadoes", "wildfire", "wildfires", "flood", "floods", "earthquake", "storm", "storms", "disaster"},
    "economy": {"economy", "economic", "inflation", "jobs", "unemployment", "recession", "prices", "wages", "market", "markets"},
    "education": {"school", "schools", "college", "colleges", "university", "universities", "student", "students", "education"},
}

US_EVENT_NOISE = set().union(*US_EVENT_GROUPS.values()) | {
    "plan", "plans", "proposal", "proposals", "propose", "proposes", "proposed", "announce", "announces", "announced",
    "could", "would", "may", "might", "people", "adults", "citizen", "citizens", "americans", "american", "nationwide",
    "win", "wins", "winning", "support", "supports", "back", "backs", "backed", "push", "pushes", "calls", "call",
}
ENTITY_NOISE = {
    "The", "A", "An", "New", "United", "States", "US", "U", "S", "President", "Presidential", "White", "House",
    "America", "American", "Americans", "Government", "Federal", "National", "Today", "Breaking", "News",
}


def _text(item):
    return " ".join(filter(None, [legacy.clean(item.findtext("title")), legacy.clean(item.findtext("description"))]))


def amount_keys(item):
    text = _text(item)
    out = set()
    for raw in re.findall(r"\$\s*([0-9][0-9,]*(?:\.\d+)?)", text):
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        out.add(f"usd:{value:g}")
    # Large explicit numbers can be event-defining even when a publisher omits '$'.
    for raw in re.findall(r"\b([1-9][0-9]{3,}|[1-9][0-9]{0,2}(?:,[0-9]{3})+)\b", text):
        try:
            value = int(raw.replace(",", ""))
        except ValueError:
            continue
        if value >= 1000:
            out.add(f"num:{value}")
    return out


def entity_keys(item):
    title = legacy.title_without_source(item)
    words = re.findall(r"\b(?:[A-Z][a-z]{2,}|[A-Z]{2,})\b", title)
    return {w.lower() for w in words if w not in ENTITY_NOISE}


def event_groups(item):
    ts = legacy.tokens(item)
    return {name for name, terms in US_EVENT_GROUPS.items() if ts & terms}


def specific_tokens(item):
    return legacy.content_tokens(item) - US_EVENT_NOISE


def same_us_event(a, b):
    """Conservatively identify differently-worded coverage of the same U.S. event.

    This requires multiple independent signals. A shared politician, agency, or topic
    by itself is never enough; that prevents one prominent person from collapsing an
    entire tab into a single cluster.
    """
    ca = legacy.clean(a.findtext("category")).strip().lower()
    cb = legacy.clean(b.findtext("category")).strip().lower()
    if ca != "us" or cb != "us":
        return False

    shared_groups = event_groups(a) & event_groups(b)
    if not shared_groups:
        return False

    shared_amounts = amount_keys(a) & amount_keys(b)
    shared_entities = entity_keys(a) & entity_keys(b)
    shared_specific = specific_tokens(a) & specific_tokens(b)

    # Distinctive amount/number + event family + one additional anchor is strong.
    if shared_amounts and (shared_entities or shared_specific):
        return True

    # Without a distinctive number, demand both a shared named entity and at least
    # three specific content anchors. This catches one event phrased several ways
    # without merging unrelated stories about the same politician or institution.
    if shared_entities and len(shared_specific) >= 3:
        return True

    return False


def event_dedupe_pass(news_file=NEWS_FILE, write_report=True):
    tree = ET.parse(news_file)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    items = channel.findall("item")
    kept = []
    removed = []
    for item in items:
        prior_match = next((prior for prior in kept if same_us_event(item, prior)), None)
        if prior_match is not None:
            removed.append({
                "category": "us",
                "removed": legacy.title_without_source(item),
                "kept": legacy.title_without_source(prior_match),
                "sharedGroups": sorted(event_groups(item) & event_groups(prior_match)),
                "sharedAmounts": sorted(amount_keys(item) & amount_keys(prior_match)),
                "sharedEntities": sorted(entity_keys(item) & entity_keys(prior_match)),
                "sharedTokens": sorted(specific_tokens(item) & specific_tokens(prior_match)),
            })
            continue
        kept.append(item)

    for item in items:
        channel.remove(item)
    for item in kept:
        channel.append(item)
    tree.write(news_file, encoding="utf-8", xml_declaration=True)

    if write_report:
        REPORT_FILE.write_text(json.dumps({
            "mode": "event-cluster-dedupe",
            "inputArticles": len(items),
            "outputArticles": len(kept),
            "removedEventDuplicates": len(removed),
            "categories": dict(Counter(r["category"] for r in removed)),
            "clusters": removed,
        }, indent=2), encoding="utf-8")

    print(f"Removed {len(removed)} additional same-event U.S. stories.")
    for row in removed[:20]:
        print(f"EVENT DUPLICATE: {row['removed']} -> {row['kept']}")
    return removed


def main():
    # Preserve every existing dedupe/language rule exactly, then add the event layer.
    legacy.main()
    event_dedupe_pass()


if __name__ == "__main__":
    main()
