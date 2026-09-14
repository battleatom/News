#!/usr/bin/env python3
"""Build a current, source-diverse Entertainment pool.

Pipeline:
collect broadly -> validate relevance -> cluster same-event coverage ->
score coverage/recency/impact/source -> retain one lead + supporting links -> rank.

Entertainment may look back up to four days for an event's strongest lead, but an
older lead is publishable only when the same event also has fresh coverage inside
the normal 48-hour window. Adult-industry content is never collected. Box Office
is untouched.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import update_news_v4 as v4

core = v4.core
NEWS = Path("News")
TARGET = 30
MIN_HEALTHY = 15
FINAL_SOURCE_CAP = 6
FRESH_HOURS = 48
LOOKBACK_HOURS = 96

# Keep discovery queries broad. Relevance, event clustering, source diversity, and
# ranking happen after collection; over-specific Google queries were starving major
# stories that did not contain every requested keyword.
BROAD_QUERIES = (
    "entertainment news",
    "celebrity news",
    "Hollywood news",
    "television entertainment",
    "movie entertainment",
    "music entertainment",
    "celebrity controversy",
    "celebrity backlash",
    "celebrity arrest court",
    "celebrity divorce relationship",
    "entertainment awards",
)
SOURCE_QUERIES = (
    ("The Hollywood Reporter", "site:hollywoodreporter.com entertainment celebrity"),
    ("Variety", "site:variety.com entertainment celebrity"),
    ("Deadline", "site:deadline.com entertainment Hollywood"),
    ("Billboard", "site:billboard.com entertainment music"),
    ("People", "site:people.com celebrity entertainment"),
    ("E! News", "site:eonline.com celebrity entertainment"),
    ("Rolling Stone", "site:rollingstone.com entertainment celebrity"),
    ("Entertainment Weekly", "site:ew.com entertainment celebrity"),
    ("BBC", "site:bbc.com entertainment celebrity"),
    ("NBC News", "site:nbcnews.com entertainment celebrity"),
    ("USA Today", "site:usatoday.com entertainment celebrity"),
    ("CBS News", "site:cbsnews.com entertainment celebrity"),
    ("ABC News", "site:abcnews.go.com entertainment celebrity"),
    ("The Guardian", "site:theguardian.com culture entertainment"),
    ("Yahoo News", "site:yahoo.com entertainment celebrity"),
    ("InStyle", "site:instyle.com celebrity entertainment"),
)

ENTERTAINMENT_SIGNALS = (
    "actor", "actress", "singer", "rapper", "musician", "artist", "band", "director",
    "filmmaker", "producer", "comedian", "celebrity", "hollywood", "film", "movie",
    "television", " tv ", "series", "streaming", "netflix", "hbo", "disney+", "prime video",
    "album", "song", "single", "tour", "concert", "music", "entertainment", "award",
    "emmy", "grammy", "oscar", "golden globe", "sag-aftra", "premiere", "festival",
    "dating", "relationship", "boyfriend", "girlfriend", "wife", "husband", "divorce",
    "married", "wedding", "pregnant", "pregnancy", "baby", "children", "family",
    "backlash", "controversy", "scandal", "red carpet", "fashion", "court documents",
    "detained", "arrested", "lawsuit", "sued",
)
REJECT_TERMS = (
    "adult film", "adult entertainment", "porn star", "pornstar", "onlyfans", "fansly",
    "nude", "naked", "topless", "sex tape", "horoscope", "astrology", "death hoax",
    "fake death", "fan theory", "fan theories", "celebrity lookalike", "coupon", "promo code",
)
LOW_VALUE_TERMS = (
    "best movies", "best shows", "what to watch", "ranked list", "full list", "complete list",
    "review:", "trailer breakdown", "fan theory", "quiz", "shopping guide", "best dressed",
    "seen and heard at every", "photo gallery", "photos:", "all the looks", "every look",
    "most shocking moments", "things you missed", "film + reviews",
)
LISTICLE_RE = re.compile(r"\b\d{1,2}\s+(?:stars|moments|things|looks|outfits|ways|times|facts|photos)\b", re.I)

SPECIALIST = (
    "hollywood reporter", "variety", "deadline", "billboard", "people", "e news",
    "rolling stone", "entertainment weekly", "vulture", "pitchfork", "instyle", "tmz",
)
SOURCE_QUALITY = {
    "reuters": 65, "associatedpress": 65, "bbc": 60, "nbcnews": 58, "cbsnews": 56,
    "abcnews": 56, "usatoday": 52, "theguardian": 52, "hollywoodreporter": 62,
    "variety": 62, "deadline": 58, "billboard": 58, "rollingstone": 54,
    "entertainmentweekly": 52, "people": 48, "enews": 45, "instyle": 42,
    "yahoonews": 40, "tmz": 36,
}

EVENT_GROUPS = {
    "death-health": {"dies", "died", "death", "dead", "hospitalized", "cancer", "illness", "injury"},
    "legal": {"arrest", "arrested", "detained", "charged", "indicted", "court", "lawsuit", "sued", "investigation"},
    "controversy": {"backlash", "controversy", "criticism", "criticized", "scandal", "feud", "apology"},
    "awards": {"emmy", "emmys", "grammy", "grammys", "oscar", "oscars", "awards", "ceremony"},
    "career": {"premiere", "premieres", "cast", "casting", "joins", "starring", "film", "movie", "series", "album", "tour", "concert", "release", "festival"},
    "relationship-family": {"divorce", "dating", "boyfriend", "girlfriend", "wife", "husband", "married", "wedding", "baby", "pregnant", "pregnancy", "son", "daughter", "child", "children"},
}
AWARD_FAMILIES = {
    "emmy": ("emmy", "emmys"),
    "grammy": ("grammy", "grammys"),
    "oscar": ("oscar", "oscars", "academy awards"),
    "golden-globe": ("golden globe", "golden globes"),
}

STOP = {
    "the", "and", "for", "with", "from", "into", "after", "before", "about", "amid", "during",
    "this", "that", "says", "said", "new", "news", "latest", "update", "report", "reports",
    "actor", "actress", "celebrity", "entertainment", "hollywood", "film", "movie", "music",
    "television", "series", "star", "stars", "exclusive", "reveals", "revealed",
}
ENTITY_NOISE = {
    "The Hollywood Reporter", "Associated Press", "USA Today", "NBC News", "CBS News",
    "ABC News", "Yahoo News", "New York", "Los Angeles", "United States",
}


def source_key(source: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "", (source or "").lower())
    if key.startswith("the") and key[3:] in SOURCE_QUALITY:
        return key[3:]
    return key


def parse_date(value: str) -> datetime:
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def age_hours(item: dict, now: datetime) -> float:
    published = item.get("published")
    if not isinstance(published, datetime):
        return 1e9
    return max(0.0, (now - published).total_seconds() / 3600.0)


def node_to_item(node: ET.Element) -> dict:
    item = {child.tag: (child.text or "").strip() for child in node if child.tag not in {"relatedArticles", "underreportedLinks"}}
    item["published"] = parse_date(item.get("pubDate", ""))
    item["category"] = "entertainment"
    return item


def text(item: dict) -> str:
    return f" {item.get('title','')} {item.get('description','')} ".lower()


def title_terms(item: dict) -> set[str]:
    return {
        w for w in re.findall(r"[a-z0-9]+", (item.get("title") or "").lower())
        if len(w) >= 3 and w not in STOP
    }


def entities(item: dict) -> set[str]:
    raw = item.get("title") or ""
    out = set()
    for phrase in re.findall(r"\b(?:[A-Z][A-Za-z'’.-]+)(?:\s+(?:[A-Z][A-Za-z'’.-]+)){1,3}\b", raw):
        phrase = phrase.strip(" -–—:,.")
        if phrase and phrase not in ENTITY_NOISE:
            out.add(phrase.lower())
    return out


def groups(item: dict) -> set[str]:
    words = title_terms(item)
    low = (item.get("title") or "").lower()
    return {name for name, anchors in EVENT_GROUPS.items() if words & anchors or any(a in low for a in anchors if " " in a)}


def award_family(item: dict) -> str:
    low = (item.get("title") or "").lower()
    for family, aliases in AWARD_FAMILIES.items():
        if any(alias in low for alias in aliases):
            return family
    return ""


def relevant(item: dict) -> bool:
    full = text(item)
    title = (item.get("title") or "").lower()
    if any(term in full for term in REJECT_TERMS):
        return False
    if any(term in title for term in LOW_VALUE_TERMS) or LISTICLE_RE.search(title):
        return False
    if any(term in full for term in ENTERTAINMENT_SIGNALS):
        return True
    source = (item.get("source") or "").lower()
    if any(token in source for token in SPECIALIST) and entities(item):
        return bool(groups(item) or re.search(r"\b(says|shares|faces|announces|returns|leaves|splits|speaks|responds)\b", title))
    return False


def same_event(a: dict, b: dict) -> bool:
    af, bf = award_family(a), award_family(b)
    if af and af == bf:
        return True

    ta, tb = title_terms(a), title_terms(b)
    if not ta or not tb:
        return False
    shared = ta & tb
    smaller = max(1, min(len(ta), len(tb)))
    if len(shared) >= 4:
        return True
    if len(shared) >= 3 and len(shared) / smaller >= 0.50:
        return True
    shared_entities = entities(a) & entities(b)
    shared_groups = groups(a) & groups(b)
    if shared_entities and shared_groups and len(shared) >= 2:
        return True
    return False


def source_bonus(item: dict) -> int:
    key = source_key(item.get("source", ""))
    return SOURCE_QUALITY.get(key, 45 if any(token.replace(" ", "") in key for token in SPECIALIST) else 25)


def importance(item: dict) -> tuple[int, str]:
    gs = groups(item)
    if "death-health" in gs:
        return 440, "MAJOR"
    if "legal" in gs:
        return 430, "MAJOR"
    if "controversy" in gs:
        return 380, "CURRENT"
    if "awards" in gs:
        return 370, "AWARDS"
    if "career" in gs:
        return 340, "CAREER"
    if "relationship-family" in gs:
        return 310, "PEOPLE"
    return 275, "ENTERTAINMENT"


def coverage_bonus(n: int) -> int:
    if n >= 5:
        return 390
    if n == 4:
        return 330
    if n == 3:
        return 260
    if n == 2:
        return 180
    return 0


def recency_bonus(item: dict, now: datetime) -> int:
    return max(0, int(190 - age_hours(item, now) * 5))


def cluster_candidates(candidates: list[dict]) -> list[list[dict]]:
    ordered = sorted(candidates, key=lambda x: x.get("published", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    clusters: list[list[dict]] = []
    for item in ordered:
        for cluster in clusters:
            if any(same_event(item, other) for other in cluster):
                cluster.append(item)
                break
        else:
            clusters.append([item])
    return clusters


def choose_representative(cluster: list[dict], source_counts: dict[str, int], now: datetime) -> dict | None:
    ranked = sorted(
        cluster,
        key=lambda x: (source_bonus(x), recency_bonus(x, now), len(x.get("title") or "")),
        reverse=True,
    )
    for item in ranked:
        if source_counts.get(source_key(item.get("source", "")), 0) < FINAL_SOURCE_CAP:
            return item
    return None


def rank_events(candidates: list[dict], limit: int = TARGET, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    unique = {}
    for item in candidates:
        if not relevant(item) or age_hours(item, now) > LOOKBACK_HOURS:
            continue
        key = core.key(item) or (item.get("link") or item.get("title") or "")
        if not key:
            continue
        prior = unique.get(key)
        if prior is None or item.get("published", now) > prior.get("published", datetime.min.replace(tzinfo=timezone.utc)):
            unique[key] = item

    event_rows = []
    for cluster in cluster_candidates(list(unique.values())):
        if not any(age_hours(x, now) <= FRESH_HOURS for x in cluster):
            continue
        sources = {source_key(x.get("source", "")) for x in cluster if x.get("source")}
        best_importance = max((importance(x)[0] for x in cluster), default=0)
        freshest = max((recency_bonus(x, now) for x in cluster), default=0)
        best_source = max((source_bonus(x) for x in cluster), default=0)
        event_score = best_importance + coverage_bonus(len(sources)) + freshest + best_source
        event_rows.append((event_score, cluster, len(sources)))
    event_rows.sort(key=lambda row: (row[0], max(x.get("published", now) for x in row[1])), reverse=True)

    selected = []
    source_counts: dict[str, int] = {}
    for event_score, cluster, source_count in event_rows:
        rep = choose_representative(cluster, source_counts, now)
        if rep is None:
            continue
        copy = dict(rep)
        _, label = importance(copy)
        copy["entertainmentSafety"] = "clean"
        copy["entertainmentLabel"] = label
        copy["entertainmentScore"] = int(event_score)
        copy["entertainmentCoverage"] = source_count
        copy["entertainmentTier"] = "ranked"
        related = []
        for other in sorted(cluster, key=lambda x: (source_bonus(x), x.get("published", now)), reverse=True):
            if other is rep or source_key(other.get("source", "")) == source_key(rep.get("source", "")):
                continue
            related.append({"title": other.get("title", ""), "link": other.get("link", ""), "source": other.get("source", "")})
            if len(related) >= 4:
                break
        if related:
            copy["_relatedArticles"] = related
        selected.append(copy)
        skey = source_key(copy.get("source", ""))
        source_counts[skey] = source_counts.get(skey, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def fetch_lookback(query: str) -> ET.Element:
    q = urllib.parse.quote(f"{query} when:4d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NewsBrief/2.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read())


def fetch_candidates() -> list[dict]:
    extra = {"instyle", "yahoo entertainment", "yahoo news"}
    core.TRUSTED_SOURCE_TOKENS = tuple(sorted(set(core.TRUSTED_SOURCE_TOKENS) | extra))
    out = []

    # Unlike core.fetch(), this stage genuinely requests when:4d from Google News.
    # The normal app remains 48h; rank_events only permits an older lead when the same
    # event has fresh <=48h follow-up coverage.
    original_age = core.MAX_AGE_HOURS
    core.MAX_AGE_HOURS = LOOKBACK_HOURS
    try:
        parser = getattr(v4, "_original_parse_items", core.parse_items)
        for query in BROAD_QUERIES:
            try:
                batch = parser(fetch_lookback(query), "entertainment")
                out.extend(batch)
                print(f"entertainment broad/{query}: {len(batch)} accepted")
            except Exception as exc:
                print(f"Entertainment broad query failed: {query}: {exc}")
        for source, query in SOURCE_QUERIES:
            try:
                batch = parser(fetch_lookback(query), "entertainment", source_override=source)
                out.extend(batch)
                print(f"entertainment source/{source}: {len(batch)} accepted")
            except Exception as exc:
                print(f"Entertainment source query failed: {source}: {exc}")
    finally:
        core.MAX_AGE_HOURS = original_age
    return out


def add_text(parent: ET.Element, tag: str, value) -> None:
    el = ET.SubElement(parent, tag)
    el.text = str(value or "")


def item_node(item: dict) -> ET.Element:
    node = ET.Element("item")
    fields = (
        "title", "link", "description", "pubDate", "source", "category", "region", "state",
        "marketId", "marketCity", "marketState", "latitude", "longitude", "imageUrl",
        "entertainmentTier", "entertainmentSafety", "entertainmentLabel", "entertainmentScore",
        "entertainmentCoverage", "whyMatters",
    )
    item["category"] = "entertainment"
    for tag in fields:
        add_text(node, tag, item.get(tag, ""))
    related = item.get("_relatedArticles", [])
    if related:
        holder = ET.SubElement(node, "relatedArticles")
        for rel in related:
            art = ET.SubElement(holder, "article")
            add_text(art, "title", rel.get("title", ""))
            add_text(art, "link", rel.get("link", ""))
            add_text(art, "source", rel.get("source", ""))
    guid = hashlib.sha1(f"{item.get('link','')}|entertainment".encode("utf-8")).hexdigest()
    guid_el = ET.SubElement(node, "guid", {"isPermaLink": "false"})
    guid_el.text = guid
    return node


def main() -> None:
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("News RSS is missing channel")
    old_nodes = [n for n in channel.findall("item") if (n.findtext("category") or "").strip() == "entertainment"]
    existing = [node_to_item(n) for n in old_nodes]
    fetched = fetch_candidates()
    selected = rank_events(existing + fetched)
    if len(selected) < MIN_HEALTHY:
        raise SystemExit(f"Entertainment refinement refused to publish thin pool: {len(selected)} < {MIN_HEALTHY}")
    for node in old_nodes:
        channel.remove(node)
    for item in selected:
        channel.append(item_node(item))
    ET.indent(tree, space="  ")
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Entertainment relevance ranking: {len(existing)} existing + {len(fetched)} discovered -> {len(selected)} ranked event leads")
    for i, item in enumerate(selected[:15], 1):
        print(f"  {i:02d}. score={item.get('entertainmentScore')} coverage={item.get('entertainmentCoverage')} source={item.get('source')} | {item.get('title')}")


if __name__ == "__main__":
    main()
