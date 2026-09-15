#!/usr/bin/env python3
"""Conservative V5.3 quality layer for the isolated quality-lab branch.

Goals:
- canonicalize publisher identity for ranking/diagnostics without changing display names;
- add source-quality and category-confidence metadata;
- separate publisher geography from story geography where it can be inferred safely;
- improve per-source story order while preserving the exact B2 publisher sequence;
- emit collector/source health diagnostics instead of adding brittle hard filters.

This script does NOT alter UX, D/NR/NW pools, category ownership, or story counts.
"""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

NEWS = Path("News")
REPORT = Path("/tmp/v53-quality-report.json")

ALIASES = {
    "ap": "associatedpress", "apnews": "associatedpress", "associatedpressnews": "associatedpress",
    "associatedpress": "associatedpress", "reuters": "reuters", "bbcnews": "bbc", "bbccom": "bbc",
    "theguardian": "guardian", "guardian": "guardian", "pbs": "pbsnewshour", "pbsnewshour": "pbsnewshour",
    "thenewyorktimes": "nytimes", "newyorktimes": "nytimes", "nytimes": "nytimes",
    "thewashingtonpost": "washingtonpost", "washingtonpost": "washingtonpost",
    "peoplecom": "people", "people": "people", "ew": "entertainmentweekly",
    "entertainmentweekly": "entertainmentweekly", "cbssports": "cbssports", "cbsnews": "cbsnews",
    "nfl": "nflcom", "nflcom": "nflcom", "profootballtalk": "profootballtalk",
    "nbcsports": "nbcsports", "foxsports": "foxsports", "yahoosports": "yahoosports",
    "sourcenewmexico": "sourcenewmexico", "krqecom": "krqe", "krqe": "krqe",
    "kob4": "kob4", "koatcom": "koat", "koat": "koat",
}

# Operational/editorial rating, not political-bias scoring. 100 = strongest primary/specialist signal.
SOURCE_QUALITY = {
    "reuters": 96, "associatedpress": 96, "bbc": 92, "afp": 92, "npr": 90, "pbsnewshour": 90,
    "bloomberg": 90, "financialtimes": 90, "nytimes": 89, "washingtonpost": 88,
    "nbcnews": 86, "cbsnews": 86, "abcnews": 86, "cnn": 84, "foxnews": 84,
    "guardian": 84, "aljazeera": 85, "france24": 84, "deutschewelle": 86, "dw": 86,
    "cbc": 86, "nhk": 88, "thehindu": 84, "southchinamorningpost": 82, "timesofindia": 80,
    "kyivindependent": 84, "haaretz": 84, "politico": 86, "axios": 85, "thehill": 80,
    "cnbc": 84, "usatoday": 80, "time": 82,
    "nflcom": 94, "espn": 91, "cbssports": 89, "nbcsports": 89, "foxsports": 87,
    "yahoosports": 84, "profootballtalk": 87, "theathletic": 91,
    "arstechnica": 94, "theverge": 91, "wired": 91, "techcrunch": 86, "ieeespectrum": 95,
    "mittechnologyreview": 95, "tomshardware": 88, "cnet": 84, "zdnet": 84, "engadget": 84,
    "ign": 90, "pcgamer": 89, "gamespot": 87, "polygon": 86, "eurogamer": 89,
    "nintendolife": 86, "defensenews": 94, "breakingdefense": 94, "militarytimes": 91,
    "thewarzone": 91, "usninews": 94, "starsandstripes": 92,
    "variety": 93, "hollywoodreporter": 93, "deadline": 91, "billboard": 91,
    "rollingstone": 86, "entertainmentweekly": 88, "people": 84,
    "sourcenewmexico": 92, "newmexicoindepth": 93, "searchlightnewmexico": 92,
    "krqe": 87, "kob4": 87, "koat": 87, "santafenewmexican": 88,
    "tricityrecord": 89, "durangoherald": 87, "navajotimes": 91,
    "congressgov": 100, "newmexicolegislature": 100, "federalregister": 100, "whitehouse": 98,
}

PUBLISHER_COUNTRY = {
    "reuters": "Global", "associatedpress": "United States", "bbc": "United Kingdom",
    "guardian": "United Kingdom", "aljazeera": "Qatar", "france24": "France",
    "deutschewelle": "Germany", "dw": "Germany", "cbc": "Canada", "nhk": "Japan",
    "thehindu": "India", "southchinamorningpost": "Hong Kong", "timesofindia": "India",
    "kyivindependent": "Ukraine", "haaretz": "Israel", "npr": "United States",
    "pbsnewshour": "United States", "nytimes": "United States", "washingtonpost": "United States",
}

CATEGORY_TERMS = {
    "world": ("world","international","ukraine","russia","china","iran","israel","gaza","europe","africa","asia","nato","foreign","global","election","war","government"),
    "us": ("u.s.","united states","american","nationwide","state","federal","supreme court","economy","congress"),
    "presidential": ("trump","president","white house","administration","executive order","oval office"),
    "federal": ("federal","congress","senate","house","supreme court","doj","fbi","dhs","irs","treasury","epa"),
    "nm": ("new mexico","albuquerque","santa fe","las cruces","farmington","rio rancho","navajo"),
    "nfl": ("nfl","football","quarterback","touchdown","coach","roster","trade","injury","chiefs","cowboys","broncos"),
    "technology": ("ai","artificial intelligence","software","hardware","cyber","chip","semiconductor","iphone","android","apple","google","microsoft","openai","cloud","data center"),
    "gaming": ("game","gaming","playstation","xbox","nintendo","switch","steam","dlc","esports","gameplay"),
    "military": ("military","army","navy","air force","marines","pentagon","defense","missile","troops","warship","fighter","drone"),
    "entertainment": ("movie","film","tv","series","actor","actress","celebrity","music","album","singer","hollywood","emmy","grammy","oscar"),
}

COUNTRY_TERMS = {
    "Ukraine": ("ukraine","ukrainian","kyiv"), "Russia": ("russia","russian","moscow"),
    "China": ("china","chinese","beijing"), "Japan": ("japan","japanese","tokyo"),
    "India": ("india","indian","delhi"), "Israel": ("israel","israeli"),
    "Palestinian Territories": ("gaza","palestinian","west bank"), "Iran": ("iran","iranian","tehran"),
    "United Kingdom": ("united kingdom","britain","british","london"), "France": ("france","french","paris"),
    "Germany": ("germany","german","berlin"), "Canada": ("canada","canadian"),
    "Mexico": ("mexico","mexican"), "Brazil": ("brazil","brazilian"),
    "United States": ("united states","u.s.","american","washington"),
}


def text(item, tag):
    return (item.findtext(tag) or "").strip()


def norm_source(value: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    if raw.startswith("the") and len(raw) > 5:
        candidate = raw[3:]
        if candidate in SOURCE_QUALITY or candidate in ALIASES:
            raw = candidate
    return ALIASES.get(raw, raw or "unknown")


def set_tag(item, tag, value):
    el = item.find(tag)
    if el is None:
        el = ET.SubElement(item, tag)
    el.text = str(value)


def body_text(item):
    parts = [text(item, x) for x in ("title","description","contentBrief","whyMatters","whatItDoes")]
    return " ".join(x for x in parts if x)


def infer_story_country(item):
    hay = body_text(item).lower()
    hits = []
    for country, terms in COUNTRY_TERMS.items():
        n = sum(1 for term in terms if term in hay)
        if n:
            hits.append((n, country))
    if not hits:
        return ""
    hits.sort(reverse=True)
    if len(hits) > 1 and hits[0][0] == hits[1][0]:
        return ""
    return hits[0][1]


def source_quality(item):
    sid = norm_source(text(item, "source"))
    return SOURCE_QUALITY.get(sid, 72)


def category_confidence(item):
    cat = text(item, "category").lower()
    if cat in {"top","x","underreported","legislation","local","region"}:
        return 85
    hay = body_text(item).lower()
    terms = CATEGORY_TERMS.get(cat, ())
    hits = sum(1 for term in terms if term in hay)
    score = 42 + min(38, hits * 8)
    src = norm_source(text(item, "source"))
    specialist = {
        "nfl": {"nflcom","espn","cbssports","nbcsports","foxsports","yahoosports","profootballtalk","theathletic"},
        "technology": {"arstechnica","theverge","wired","techcrunch","ieeespectrum","mittechnologyreview","tomshardware","cnet","zdnet","engadget"},
        "gaming": {"ign","pcgamer","gamespot","polygon","eurogamer","nintendolife"},
        "military": {"defensenews","breakingdefense","militarytimes","thewarzone","usninews","starsandstripes"},
        "entertainment": {"variety","hollywoodreporter","deadline","billboard","rollingstone","entertainmentweekly","people"},
    }
    if src in specialist.get(cat, set()):
        score += 12
    return max(0, min(100, score))


def information_score(item):
    title = text(item, "title")
    body = body_text(item)
    tokens = re.findall(r"[A-Za-z0-9]+", title)
    score = min(18, len(tokens) * 1.2)
    if len(body) >= 180: score += 12
    elif len(body) >= 90: score += 7
    if re.search(r"\b\d[\d,.%$-]*\b", title): score += 3
    if re.search(r"\b(live|watch|photos|what to know|everything we know|latest updates)\b", title, re.I): score -= 5
    return max(0, min(30, score))


def total_quality(item):
    sq = source_quality(item)
    cc = category_confidence(item)
    info = information_score(item)
    # Reliability/relevance dominate; information richness is a modest tie-breaker.
    return round(sq * 0.44 + cc * 0.46 + info * (10/30), 2)


def reorder_with_same_source_pattern(items):
    """Improve article order inside each publisher while preserving B2's exact publisher sequence."""
    buckets = defaultdict(list)
    pattern = []
    for pos, item in enumerate(items):
        sid = norm_source(text(item, "source"))
        pattern.append(sid)
        buckets[sid].append((pos, item))
    for sid in buckets:
        buckets[sid].sort(key=lambda pair: (-total_quality(pair[1]), pair[0]))
    offsets = Counter()
    output = []
    for sid in pattern:
        idx = offsets[sid]
        output.append(buckets[sid][idx][1])
        offsets[sid] += 1
    return output


def main():
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")
    items = list(channel.findall("item"))
    by_cat = defaultdict(list)
    for item in items:
        by_cat[text(item, "category").lower()].append(item)

    diagnostics = {}
    low_conf = []
    for cat, arr in by_cat.items():
        source_counts = Counter()
        scores = []
        publisher_countries = Counter()
        story_countries = Counter()
        for item in arr:
            sid = norm_source(text(item, "source"))
            sq = source_quality(item); cc = category_confidence(item); tq = total_quality(item)
            pc = PUBLISHER_COUNTRY.get(sid, "")
            sc = infer_story_country(item)
            set_tag(item, "canonicalSource", sid)
            set_tag(item, "sourceQualityScore", sq)
            set_tag(item, "categoryConfidence", cc)
            set_tag(item, "v53QualityScore", tq)
            if pc: set_tag(item, "publisherCountry", pc)
            if sc: set_tag(item, "storyCountry", sc)
            source_counts[sid] += 1; scores.append(tq)
            if pc: publisher_countries[pc] += 1
            if sc: story_countries[sc] += 1
            if cc < 50:
                low_conf.append({"category":cat,"source":text(item,"source"),"title":text(item,"title"),"confidence":cc})

        diagnostics[cat] = {
            "count": len(arr),
            "uniqueCanonicalSources": len(source_counts),
            "topSources": source_counts.most_common(10),
            "averageQuality": round(sum(scores)/len(scores),2) if scores else 0,
            "publisherCountries": publisher_countries.most_common(10),
            "storyCountries": story_countries.most_common(10),
        }

    # Refill each category's positions with the same publisher pattern but better per-source story order.
    replacement = {cat: iter(reorder_with_same_source_pattern(arr)) for cat, arr in by_cat.items()}
    for item in items:
        channel.remove(item)
    # Preserve category block order from the original feed.
    for cat in by_cat:
        for item in replacement[cat]:
            channel.append(item)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    report = {
        "model": "v53-conservative-quality-layer",
        "storyCountUnchanged": len(items),
        "sourcePatternPreserved": True,
        "hardDeletes": 0,
        "lowConfidenceReviewCount": len(low_conf),
        "lowConfidenceReview": low_conf[:80],
        "tabs": diagnostics,
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
