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
MAX_RELATED_DISPLAY = 4

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

TITLE_STOP_WORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by",
    "after", "before", "new", "says", "said", "that", "this", "are", "was", "were", "has", "have", "had",
    "into", "over", "its", "their", "will", "amid", "more", "than", "report", "reports", "story", "news",
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


def title_words(value: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9]+", clean(value).lower())
        if len(word) >= 3 and word not in TITLE_STOP_WORDS
    }


def feed_url(query: str) -> str:
    q = urllib.parse.quote(f"{query} when:{MAX_DAYS}d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def item_text(item: ET.Element) -> str:
    return f"{clean(item.findtext('title'))} {clean(item.findtext('description'))}".lower()


def term_present(text: str, term: str) -> bool:
    words = [re.escape(part) for part in term.lower().split() if part]
    if not words:
        return False
    pattern = r"\b" + r"\s+".join(words) + r"\b"
    return re.search(pattern, text.lower()) is not None


def any_term(text: str, terms) -> bool:
    return any(term_present(text, term) for term in terms)


def underreported_eligible(item: ET.Element) -> bool:
    text = item_text(item)
    source = clean(item.findtext("source")).lower()
    public_interest = any_term(text, PUBLIC_INTEREST_TERMS)
    low_value_signal = any_term(text, LOW_VALUE_TECH_GAMING_TERMS)
    low_value_source = source in LOW_VALUE_TECH_GAMING_SOURCES
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
            req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 UnderreportedPriority/2.0"})
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
    age_hours = max(0.0, (now - dt).total_seconds() / 3600)
    if age_hours <= 6: return 100
    if age_hours <= 24: return 95
    if age_hours <= 48: return 88
    if age_hours <= 72: return 78
    if age_hours <= 120: return 62
    if age_hours <= 168: return 48
    if age_hours <= 240: return 32
    if age_hours <= MAX_DAYS * 24: return 15
    return 0


def age_band(dt, now) -> str:
    if not dt:
        return "unknown"
    d = max(0.0, (now - dt).total_seconds() / 86400)
    if d <= 2: return "blue"
    if d <= 4: return "green"
    if d <= 7: return "orange"
    if d <= 10: return "purple"
    return "red"


def coverage_nodes(item: ET.Element) -> list[ET.Element]:
    pool = item.findall("coveragePool/article")
    if pool:
        return pool
    related = item.findall("related/article")
    if related:
        return related
    return item.findall("relatedArticles/article")


def source_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def distinct_supporting_sources(item: ET.Element) -> set[str]:
    primary = source_key(item.findtext("source"))
    return {
        source_key(node.findtext("source"))
        for node in coverage_nodes(item)
        if source_key(node.findtext("source")) and source_key(node.findtext("source")) != primary
    }


def supporting_source_count(item: ET.Element) -> int:
    actual = len(distinct_supporting_sources(item))
    try:
        explicit = int(float(clean(item.findtext("supportingSourceCount")) or 0))
    except Exception:
        explicit = 0
    return max(explicit, actual)


def corroboration_score(item: ET.Element) -> int:
    count = supporting_source_count(item)
    if count <= 0: return 15
    if count == 1: return 40
    if count == 2: return 65
    if count == 3: return 80
    if count == 4: return 90
    return 100


def coverage_gap_score(item: ET.Element) -> int:
    count = supporting_source_count(item)
    if count <= 0: return 96
    if count == 1: return 92
    if count == 2: return 86
    if count == 3: return 80
    if count == 4: return 74
    if count == 5: return 68
    if count == 6: return 60
    if count == 7: return 52
    if count == 8: return 44
    if count <= 10: return 34
    if count <= 14: return 22
    return 12


def saturation_penalty(item: ET.Element) -> int:
    count = supporting_source_count(item)
    if count <= 6: return 0
    if count <= 9: return 4
    if count <= 14: return 10
    return 18


def coverage_source_windows(item: ET.Element, now) -> tuple[int, int, int]:
    primary = source_key(item.findtext("source"))
    recent6: set[str] = set()
    recent24: set[str] = set()
    prior72: set[str] = set()
    for node in coverage_nodes(item):
        src = source_key(node.findtext("source"))
        if not src or src == primary:
            continue
        dt = parse_date(node.findtext("pubDate"))
        if not dt:
            continue
        age_hours = max(0.0, (now - dt).total_seconds() / 3600)
        if age_hours <= 6:
            recent6.add(src)
        if age_hours <= 24:
            recent24.add(src)
        elif age_hours <= 72:
            prior72.add(src)
    return len(recent6), len(recent24), len(prior72)


def momentum_score(item: ET.Element, now) -> int:
    recent6, recent24, prior72 = coverage_source_windows(item, now)
    total = supporting_source_count(item)
    if recent6 >= 3: return 100
    if recent6 == 2: return 92
    if recent24 >= 5: return 95
    if recent24 >= 3 and recent24 > prior72: return 85
    if recent24 >= 2 and recent24 >= prior72: return 72
    if recent24 == 1 and prior72 <= 1: return 55
    if recent24 == 1: return 40
    if total > 0 and not any(parse_date(node.findtext("pubDate")) for node in coverage_nodes(item)):
        return 45
    return 20


def continuing_relevance_score(item: ET.Element, dt, now) -> int:
    text = item_text(item)
    age_days = max(0.0, (now - dt).total_seconds() / 86400) if dt else MAX_DAYS
    score = max(25, 70 - round(age_days * 2.5))
    if any_term(text, CONTINUING_TERMS): score += 18
    if clean(item.findtext("whatNext")): score += 8
    if clean(item.findtext("background")): score += 5
    return max(0, min(100, score))


def set_text(item: ET.Element, tag: str, value) -> None:
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = str(value)


def article_key(node: ET.Element) -> str:
    link = clean(node.findtext("link")).lower()
    if link:
        return f"link:{link}"
    title = norm_title(clean(node.findtext("title")))
    return f"title:{title}" if title else ""


def append_article(parent: ET.Element, source_node: ET.Element) -> bool:
    existing = {article_key(node) for node in parent.findall("article")}
    key = article_key(source_node)
    if not key or key in existing:
        return False
    article = ET.SubElement(parent, "article")
    for tag in ("title", "link", "description", "source", "pubDate"):
        value = clean(source_node.findtext(tag))
        if value:
            ET.SubElement(article, tag).text = value
    return True


def append_item_as_article(parent: ET.Element, item: ET.Element) -> bool:
    temp = ET.Element("article")
    for tag in ("title", "link", "description", "source", "pubDate"):
        value = clean(item.findtext(tag))
        if value:
            ET.SubElement(temp, tag).text = value
    return append_article(parent, temp)


def ensure_child(item: ET.Element, tag: str) -> ET.Element:
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    return node


def event_related_keys(item: ET.Element) -> set[str]:
    return {article_key(node) for node in coverage_nodes(item) if article_key(node)}


def same_underreported_event(a: ET.Element, b: ET.Element) -> bool:
    link_a, link_b = clean(a.findtext("link")), clean(b.findtext("link"))
    if link_a and link_b and link_a == link_b:
        return True
    if event_related_keys(a) & event_related_keys(b):
        return True
    title_a = norm_title(clean(a.findtext("title")))
    title_b = norm_title(clean(b.findtext("title")))
    related_titles_a = {norm_title(clean(n.findtext("title"))) for n in coverage_nodes(a) if clean(n.findtext("title"))}
    related_titles_b = {norm_title(clean(n.findtext("title"))) for n in coverage_nodes(b) if clean(n.findtext("title"))}
    if title_a and title_a in related_titles_b: return True
    if title_b and title_b in related_titles_a: return True
    ta, tb = title_words(title_a), title_words(title_b)
    if not ta or not tb:
        return False
    overlap = len(ta & tb)
    smaller = min(len(ta), len(tb))
    return overlap >= 4 and smaller > 0 and overlap / smaller >= 0.55


def merge_event_cluster(cluster: list[ET.Element], now) -> ET.Element:
    def representative_key(item: ET.Element):
        dt = parse_date(item.findtext("pubDate"))
        return (importance_score(item), supporting_source_count(item), freshness_score(dt, now), dt.timestamp() if dt else 0)

    primary = max(cluster, key=representative_key)
    pool = ensure_child(primary, "coveragePool")
    related = ensure_child(primary, "related")
    for other in cluster:
        if other is primary:
            continue
        append_item_as_article(pool, other)
        if len(related.findall("article")) < MAX_RELATED_DISPLAY:
            append_item_as_article(related, other)
        for node in coverage_nodes(other):
            append_article(pool, node)
            if len(related.findall("article")) < MAX_RELATED_DISPLAY:
                append_article(related, node)

    count = len(distinct_supporting_sources(primary))
    set_text(primary, "supportingSourceCount", count)
    set_text(primary, "coverageGapScore", coverage_gap_score(primary))
    set_text(primary, "underreportedScore", coverage_gap_score(primary))
    if count <= 2: set_text(primary, "coverage", "Limited supporting coverage")
    elif count <= 6: set_text(primary, "coverage", "Growing supporting coverage")
    elif count <= 9: set_text(primary, "coverage", "Broadening coverage")
    else: set_text(primary, "coverage", "Broad coverage — underreported signal weakening")
    return primary


def cluster_underreported_events(items: list[ET.Element], now) -> tuple[list[ET.Element], int]:
    if not items:
        return [], 0
    parent = list(range(len(items)))
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i, first in enumerate(items):
        for j in range(i + 1, len(items)):
            if same_underreported_event(first, items[j]):
                union(i, j)
    groups: dict[int, list[ET.Element]] = {}
    for index, item in enumerate(items):
        groups.setdefault(find(index), []).append(item)
    merged = []
    collapsed = 0
    for cluster in groups.values():
        if len(cluster) == 1:
            merged.append(cluster[0])
        else:
            merged.append(merge_event_cluster(cluster, now))
            collapsed += len(cluster) - 1
    return merged, collapsed


def ranking_components(item: ET.Element, dt, now) -> dict[str, int]:
    importance = importance_score(item)
    corroboration = corroboration_score(item)
    freshness = freshness_score(dt, now)
    coverage_gap = coverage_gap_score(item)
    momentum = momentum_score(item, now)
    continuing = continuing_relevance_score(item, dt, now)
    penalty = saturation_penalty(item)
    priority = round(
        importance * 0.25
        + corroboration * 0.20
        + freshness * 0.20
        + coverage_gap * 0.15
        + momentum * 0.10
        + continuing * 0.10
        - penalty
    )
    return {
        "importance": importance,
        "corroboration": corroboration,
        "freshness": freshness,
        "coverage_gap": coverage_gap,
        "momentum": momentum,
        "continuing": continuing,
        "saturation_penalty": penalty,
        "priority": max(0, min(100, priority)),
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

    eligible = []
    excluded = 0
    for item in under:
        dt = parse_date(item.findtext("pubDate"))
        age_days = (now - dt).total_seconds() / 86400 if dt else 999
        if age_days > MAX_DAYS or not underreported_eligible(item):
            excluded += 1
            continue
        eligible.append(item)

    event_items, collapsed = cluster_underreported_events(eligible, now)
    ranked = []
    for item in event_items:
        dt = parse_date(item.findtext("pubDate"))
        scores = ranking_components(item, dt, now)
        recent6, recent24, prior72 = coverage_source_windows(item, now)
        set_text(item, "importanceScore", scores["importance"])
        set_text(item, "corroborationScore", scores["corroboration"])
        set_text(item, "freshnessScore", scores["freshness"])
        set_text(item, "coverageGapScore", scores["coverage_gap"])
        set_text(item, "underreportedScore", scores["coverage_gap"])
        set_text(item, "coverageMomentumScore", scores["momentum"])
        set_text(item, "continuingRelevanceScore", scores["continuing"])
        set_text(item, "saturationPenalty", scores["saturation_penalty"])
        set_text(item, "recentSupportingSources6h", recent6)
        set_text(item, "recentSupportingSources24h", recent24)
        set_text(item, "priorSupportingSources72h", prior72)
        set_text(item, "underreportedPriority", scores["priority"])
        set_text(item, "ageBand", age_band(dt, now))
        ranked.append((scores["priority"], scores["freshness"], scores["momentum"], scores["importance"], scores["corroboration"], dt.timestamp() if dt else 0, item))

    ranked.sort(key=lambda row: row[:-1], reverse=True)
    selected = [row[-1] for row in ranked[:MAX_ITEMS]]
    for item in all_items:
        channel.remove(item)
    for item in top + selected + rest:
        channel.append(item)
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Underreported event ranking retained {len(selected)} stories from the last {MAX_DAYS} days; collapsed {collapsed} duplicate event card(s) and excluded {excluded} stale or low-value candidate(s).")


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
