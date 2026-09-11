#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from update_news import UNDERREPORTED_DISCOVERY_QUERIES, source_is_trusted, underreported_source_allowed

NEWS = Path("News")
MAX_DAYS = 14
MAX_ITEMS = 30

PUBLIC_INTEREST_TERMS = {
    "privacy", "surveillance", "breach", "cyberattack", "cybersecurity", "hack", "hacked", "security",
    "fraud", "scam", "lawsuit", "court", "ruling", "regulation", "regulator", "government", "congress",
    "labor", "workers", "layoffs", "union", "safety", "recall", "contamination", "public health", "civil rights",
    "discrimination", "election", "voting", "war", "military", "environment", "pollution", "water", "housing",
    "medicaid", "medicare", "hospital", "investigation", "whistleblower", "antitrust", "monopoly", "rights",
}

LOW_VALUE_TECH_GAMING_TERMS = {
    "gameplay", "trailer", "teaser", "dlc", "expansion", "definitive edition", "release date", "preorder", "pre-order",
    "review", "hands-on", "benchmark", "fps", "console", "controller", "switch 2", "playstation", "xbox", "steam deck",
    "gaming laptop", "graphics card", "gpu", "motherboard", "monitor", "keyboard", "mouse", "headset", "deal", "sale",
    "discount", "best buy", "amazon", "prime day", "black friday", "upgrade", "hardware", "retro game", "videos for pc",
}

LOW_VALUE_TECH_GAMING_SOURCES = {
    "pc gamer", "nintendo life", "gamespot", "gamefaqs", "polygon", "ign", "tech times", "hothardware",
}

CONTINUING_TERMS = {
    "investigation", "investigating", "lawsuit", "court", "ruling", "appeal", "trial", "hearing", "audit",
    "whistleblower", "recall", "outbreak", "wildfire", "drought", "flood", "war", "ceasefire", "humanitarian",
    "pollution", "cleanup", "surveillance", "medicaid", "medicare", "housing", "election", "voting", "legislation",
    "bill", "regulation", "regulator", "bankruptcy", "layoffs", "strike", "workers", "civil rights", "indigenous",
}


def clean(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str | None):
    try:
        dt = parsedate_to_datetime(clean(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def norm_title(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def feed_url(query: str) -> str:
    q = urllib.parse.quote(f"{query} when:{MAX_DAYS}d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def item_text(item: ET.Element) -> str:
    return f"{clean(item.findtext('title'))} {clean(item.findtext('description'))}".lower()


def term_present(text: str, term: str) -> bool:
    """Match whole words/phrases so 'war' does not match 'Warriors'."""
    words = [re.escape(part) for part in term.lower().split() if part]
    if not words:
        return False
    pattern = r"\b" + r"\s+".join(words) + r"\b"
    return re.search(pattern, text.lower()) is not None


def any_term(text: str, terms) -> bool:
    return any(term_present(text, term) for term in terms)


def underreported_eligible(item: ET.Element) -> bool:
    """Keep public-interest reporting while rejecting routine consumer-tech/gaming churn."""
    text = item_text(item)
    source = clean(item.findtext("source")).lower()
    public_interest = any_term(text, PUBLIC_INTEREST_TERMS)
    low_value_signal = any_term(text, LOW_VALUE_TECH_GAMING_TERMS)
    low_value_source = source in LOW_VALUE_TECH_GAMING_SOURCES

    # Product/release/review coverage from gaming/consumer-tech outlets is not
    # Underreported merely because few other outlets covered it. A genuine public-
    # interest signal can still keep a story from one of these outlets eligible.
    if (low_value_signal or low_value_source) and not public_interest:
        return False
    return True


def discover() -> None:
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")

    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - MAX_DAYS * 86400
    seen_titles = {norm_title(clean(i.findtext("title"))) for i in channel.findall("item")}
    seen_links = {clean(i.findtext("link")) for i in channel.findall("item")}
    added = 0

    for source_name, query in UNDERREPORTED_DISCOVERY_QUERIES:
        try:
            req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 UnderreportedPriority/1.1"})
            with urllib.request.urlopen(req, timeout=20) as response:
                feed = ET.fromstring(response.read())
        except Exception as exc:
            print(f"Underreported 14-day discovery failed for {source_name}: {exc}")
            continue

        for src in feed.findall(".//item"):
            title = clean(src.findtext("title"))
            link = clean(src.findtext("link"))
            desc = clean(src.findtext("description"))
            pub = clean(src.findtext("pubDate"))
            dt = parse_date(pub)
            source_el = src.find("source")
            source = source_name or clean(source_el.text if source_el is not None else "")
            if not title or not link or not dt or dt.timestamp() < cutoff or dt > now:
                continue
            if not source_is_trusted(source):
                continue
            candidate = {"title": title, "description": desc, "source": source}
            if not underreported_source_allowed(candidate):
                continue
            nt = norm_title(title)
            if nt in seen_titles or link in seen_links:
                continue
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = link
            ET.SubElement(item, "description").text = desc
            ET.SubElement(item, "pubDate").text = pub
            ET.SubElement(item, "source").text = source
            ET.SubElement(item, "category").text = "underreported"
            if not underreported_eligible(item):
                channel.remove(item)
                continue
            seen_titles.add(nt)
            seen_links.add(link)
            added += 1

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Underreported 14-day discovery added {added} eligible candidate story/stories.")


def importance_score(item: ET.Element) -> int:
    text = item_text(item)
    score = 20
    weighted = {
        "war": 16, "attack": 14, "airstrike": 14, "missile": 14, "ceasefire": 12,
        "mass shooting": 18, "shooting": 12, "killed": 10, "deaths": 10,
        "earthquake": 15, "hurricane": 15, "tornado": 14, "wildfire": 14, "flood": 10,
        "outbreak": 12, "recall": 10, "contamination": 13, "public health": 12,
        "supreme court": 14, "ruling": 11, "executive order": 12, "legislation": 10,
        "bill": 8, "audit": 12, "investigation": 13, "inspector general": 14,
        "whistleblower": 13, "civil rights": 12, "privacy": 10, "surveillance": 11,
        "medicaid": 11, "medicare": 11, "hospital": 9, "housing": 9,
        "workers": 8, "labor": 8, "layoffs": 8, "bankruptcy": 10,
        "pollution": 11, "water": 8, "drought": 9, "tribal": 10, "indigenous": 10,
        "fraud": 10, "settlement": 8, "lawsuit": 8, "election": 10, "voting": 9,
        "humanitarian": 12, "famine": 15, "refugee": 10,
    }
    for term, weight in weighted.items():
        if term_present(text, term):
            score += weight
    if any_term(text, ("opinion", "review", "podcast", "how to", "guide", "sale", "deal")):
        score -= 18
    return max(0, min(100, score))


def freshness_score(dt, now) -> int:
    if not dt:
        return 0
    age_days = max(0.0, (now - dt).total_seconds() / 86400)
    return max(0, min(100, round(100 * (1 - age_days / MAX_DAYS))))


def age_band(dt, now) -> str:
    if not dt:
        return "unknown"
    d = max(0.0, (now - dt).total_seconds() / 86400)
    if d <= 2: return "blue"
    if d <= 4: return "green"
    if d <= 7: return "orange"
    if d <= 10: return "purple"
    return "red"


def supporting_source_count(item: ET.Element) -> int:
    try:
        explicit = int(float(clean(item.findtext("supportingSourceCount")) or 0))
    except Exception:
        explicit = 0
    related_sources = {
        clean(node.findtext("source")).lower()
        for node in item.findall("related/article")
        if clean(node.findtext("source"))
    }
    return max(explicit, len(related_sources))


def corroboration_score(item: ET.Element) -> int:
    # This measures distinct supporting publishers found, not true wire-service
    # independence. Keep the score bounded so underreporting can still matter.
    count = supporting_source_count(item)
    if count <= 0: return 20
    if count == 1: return 45
    if count == 2: return 65
    if count == 3: return 80
    return 90


def continuing_relevance_score(item: ET.Element, dt, now) -> int:
    text = item_text(item)
    age_days = max(0.0, (now - dt).total_seconds() / 86400) if dt else MAX_DAYS
    score = max(25, 70 - round(age_days * 2.5))
    if any_term(text, CONTINUING_TERMS):
        score += 18
    if clean(item.findtext("whatNext")):
        score += 8
    if clean(item.findtext("background")):
        score += 5
    return max(0, min(100, score))


def set_text(item: ET.Element, tag: str, value) -> None:
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = str(value)


def ranking_components(item: ET.Element, dt, now) -> dict[str, int]:
    importance = importance_score(item)
    corroboration = corroboration_score(item)
    try:
        under_score = int(float(clean(item.findtext("underreportedScore")) or 70))
    except Exception:
        under_score = 70
    under_score = max(0, min(100, under_score))
    continuing = continuing_relevance_score(item, dt, now)
    freshness = freshness_score(dt, now)

    # Underreported should favor important, supported, still-relevant stories rather
    # than simply the newest obscure headline. Freshness is retained as metadata and
    # a tie-breaker, but is no longer a direct 30% ranking weight.
    priority = round(
        importance * 0.40
        + corroboration * 0.25
        + under_score * 0.20
        + continuing * 0.15
    )
    return {
        "importance": importance,
        "corroboration": corroboration,
        "underreported": under_score,
        "continuing": continuing,
        "freshness": freshness,
        "priority": priority,
    }


def rank() -> None:
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")
    now = datetime.now(timezone.utc)
    all_items = list(channel.findall("item"))
    top = [x for x in all_items if clean(x.findtext("category")).lower() == "top"]
    under = [x for x in all_items if clean(x.findtext("category")).lower() == "underreported"]
    rest = [x for x in all_items if clean(x.findtext("category")).lower() not in {"top", "underreported"}]

    ranked = []
    excluded = 0
    for item in under:
        dt = parse_date(item.findtext("pubDate"))
        age_days = (now - dt).total_seconds() / 86400 if dt else 999
        if age_days > MAX_DAYS or not underreported_eligible(item):
            excluded += 1
            continue

        scores = ranking_components(item, dt, now)
        band = age_band(dt, now)
        set_text(item, "importanceScore", scores["importance"])
        set_text(item, "corroborationScore", scores["corroboration"])
        set_text(item, "continuingRelevanceScore", scores["continuing"])
        set_text(item, "freshnessScore", scores["freshness"])
        set_text(item, "underreportedPriority", scores["priority"])
        set_text(item, "ageBand", band)
        ranked.append((
            scores["priority"], scores["importance"], scores["corroboration"],
            scores["continuing"], scores["freshness"], dt.timestamp() if dt else 0, item,
        ))

    ranked.sort(key=lambda row: row[:-1], reverse=True)
    selected = [row[-1] for row in ranked[:MAX_ITEMS]]

    for item in all_items:
        channel.remove(item)
    for item in top + selected + rest:
        channel.append(item)
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(
        f"Underreported priority ranking retained {len(selected)} stories from the last {MAX_DAYS} days; "
        f"excluded {excluded} stale or low-value tech/gaming candidate(s)."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--rank", action="store_true")
    args = parser.parse_args()
    if args.discover:
        discover()
    elif args.rank:
        rank()
    else:
        raise SystemExit("Use --discover or --rank")


if __name__ == "__main__":
    main()
