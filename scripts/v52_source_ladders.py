#!/usr/bin/env python3
"""V5.2 B2 per-tab source hierarchy + article ladder.

Editorial model:
  1. Every normal tab has its own ranked publisher hierarchy.
  2. Every publisher's eligible stories are independently ranked.
  3. Round 1 emits each publisher's best story, in source-rank order.
     Round 2 emits each publisher's second-best story, and so on.
  4. Approved/unlisted publishers form a fallback roster AFTER named sources;
     each fallback publisher still receives its own ranked turn.
  5. Strong exact/near duplicate cards are removed before rounds are assigned.
  6. Short/vague headlines are rejected only when the article also lacks enough
     useful explanatory content. Strong paraphrased/contextual content can save
     an otherwise terse publisher headline.

Underreported is intentionally excluded: it has a different editorial mission.
Local/Region preserve their location metadata; this script does not collapse
national inventory to the build runner's location.
"""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path

NEWS = Path("News")
REPORT = Path("/tmp/v52-source-ladders.json")

# Ranked, category-specific editorial rosters. Aliases are normalized below.
HIERARCHIES = {
    "top": [
        "Reuters", "Associated Press", "BBC", "NPR", "PBS NewsHour",
        "The New York Times", "The Washington Post", "Bloomberg", "NBC News",
        "CBS News", "ABC News", "CNN", "Fox News", "Axios", "Politico",
        "The Guardian", "CNBC", "USA Today", "Al Jazeera", "Financial Times", "TIME",
    ],
    "world": [
        "Reuters", "Associated Press", "BBC", "AFP", "Al Jazeera", "The Guardian",
        "The New York Times", "The Washington Post", "Financial Times", "CNN",
        "NBC News", "CBS News", "ABC News", "NPR", "PBS NewsHour", "Bloomberg",
    ],
    "us": [
        "Associated Press", "Reuters", "NPR", "PBS NewsHour", "The New York Times",
        "The Washington Post", "NBC News", "CBS News", "ABC News", "CNN", "Fox News",
        "USA Today", "Axios", "Politico", "The Hill", "TIME", "CNBC",
    ],
    "presidential": [
        "Associated Press", "Reuters", "Politico", "Axios", "The New York Times",
        "The Washington Post", "NBC News", "ABC News", "CBS News", "CNN", "Fox News",
        "NPR", "PBS NewsHour", "The Hill", "The Guardian",
    ],
    "federal": [
        "Associated Press", "Reuters", "Politico", "Axios", "The Hill", "NPR",
        "PBS NewsHour", "The New York Times", "The Washington Post", "NBC News",
        "ABC News", "CBS News", "CNN", "Fox News",
    ],
    "legislation": [
        "Congress.gov", "Federal Register", "White House", "New Mexico Legislature",
    ],
    "nm": [
        "Source New Mexico", "New Mexico In Depth", "Searchlight New Mexico",
        "KRQE", "KOB 4", "KOAT", "Santa Fe New Mexican", "Albuquerque Journal",
        "Tri City Record", "Navajo Times", "The Journal",
        "Associated Press", "Reuters",
    ],
    "local": [
        "Tri City Record", "The Journal", "Durango Herald", "Navajo Times",
        "Source New Mexico", "Associated Press", "Reuters", "CBS News", "NBC News", "ABC News",
    ],
    "region": [
        "Source New Mexico", "Arizona Daily Sun", "Colorado Public Radio", "KSL.com",
        "KRDO", "KOAA News 5", "Associated Press", "Reuters", "CBS News", "NBC News", "ABC News",
    ],
    "nfl": [
        "NFL.com", "ESPN", "CBS Sports", "NBC Sports", "Fox Sports", "Yahoo Sports",
        "ProFootballTalk", "The Athletic", "USA Today",
    ],
    "technology": [
        "Ars Technica", "The Verge", "WIRED", "TechCrunch", "IEEE Spectrum",
        "MIT Technology Review", "Tom's Hardware", "CNET", "ZDNET", "Engadget",
        "9to5Mac", "Android Authority", "PCMag", "Reuters", "Bloomberg", "CNBC",
    ],
    "gaming": [
        "IGN", "PlayStation Blog", "Nintendo", "Xbox Wire", "Kotaku", "PC Gamer",
        "GameSpot", "Polygon", "Eurogamer", "Nintendo Life", "VGC", "GamesIndustry.biz",
        "Rock Paper Shotgun", "Game Informer",
    ],
    "military": [
        "Defense News", "Breaking Defense", "Military Times", "The War Zone", "USNI News",
        "Task & Purpose", "Stars and Stripes", "Reuters", "Associated Press", "BBC",
    ],
    "entertainment": [
        "Variety", "The Hollywood Reporter", "Deadline", "Billboard", "Rolling Stone",
        "Entertainment Weekly", "People", "Pitchfork", "Vulture", "E! News", "TMZ",
        "Page Six", "BBC", "USA Today", "The Guardian",
    ],
}

ALIASES = {
    "apnews": "associatedpress", "ap": "associatedpress", "associatedpressnews": "associatedpress",
    "bbcnews": "bbc", "bbccom": "bbc", "theguardian": "guardian", "guardian": "guardian",
    "newyorktimes": "nytimes", "thenewyorktimes": "nytimes", "washingtonpost": "washingtonpost",
    "thewashingtonpost": "washingtonpost", "usatodaycom": "usatoday", "time magazine": "time",
    "time": "time", "pbsnewshour": "pbsnewshour", "pbs": "pbsnewshour",
    "hollywoodreporter": "hollywoodreporter", "thehollywoodreporter": "hollywoodreporter",
    "wired": "wired", "wiredcom": "wired", "kob4": "kob4", "krqecom": "krqe",
    "koatcom": "koat", "tricityrecord": "tricityrecord", "thejournal": "thejournal",
    "the-journalcom": "thejournal", "nfl": "nflcom", "nflcom": "nflcom",
    "playstationblog": "playstationblog", "blogplaystationcom": "playstationblog",
    "xboxwire": "xboxwire", "newsxboxcom": "xboxwire", "nintendocom": "nintendo",
    "gamesindustrybiz": "gamesindustrybiz", "rockpapershotgun": "rockpapershotgun",
    "usninews": "usninews", "taskpurpose": "taskpurpose", "taskandpurpose": "taskpurpose",
    "starsandstripes": "starsandstripes", "ew": "entertainmentweekly",
    "entertainmentweekly": "entertainmentweekly", "enews": "enews", "e!news": "enews",
    "sourcenewmexico": "sourcenewmexico", "newmexicoindepth": "newmexicoindepth",
    "searchlightnewmexico": "searchlightnewmexico", "santafenewmexican": "santafenewmexican",
    "albuquerquejournal": "albuquerquejournal", "navajotimes": "navajotimes",
}

STOP = {
    "the","a","an","of","to","in","on","for","and","or","as","at","by","from","with","after","before",
    "is","are","was","were","be","been","being","this","that","these","those","new","latest","news","says",
    "say","amid","over","about","into","its","their","his","her","your","our","more","what","why","how",
}

VAGUE = re.compile(
    r"^(latest|update|updates|live|watch|video|photos?|what to know|everything we know|here'?s what|breaking news)\b|"
    r"\b(latest updates|live updates|what we know so far|everything you need to know)\b",
    re.I,
)

CATEGORY_ANCHORS = {
    "world": r"\b(world|international|ukraine|russia|china|iran|israel|gaza|europe|africa|asia|nato|foreign|global|border|war|election)\b",
    "us": r"\b(u\.s\.|us |united states|american|nationwide|federal|state|supreme court|economy|inflation|congress)\b",
    "presidential": r"\b(president|white house|trump|administration|executive order|presidential)\b",
    "federal": r"\b(federal|congress|senate|house|supreme court|appeals court|doj|fbi|dhs|epa|ftc|sec|fcc|irs|treasury)\b",
    "nm": r"\b(new mexico|albuquerque|santa fe|las cruces|farmington|rio rancho|navajo nation|nm )\b",
    "nfl": r"\b(nfl|touchdown|quarterback|super bowl|football|coach|wide receiver|running back|linebacker|draft|team)\b",
    "technology": r"\b(ai|artificial intelligence|software|hardware|cyber|chip|semiconductor|iphone|android|apple|google|microsoft|openai|anthropic|robot|data center|cloud|app|device)\b",
    "gaming": r"\b(game|gaming|playstation|ps5|xbox|nintendo|switch|steam|pc gamer|gameplay|dlc|esports|studio|developer|release)\b",
    "military": r"\b(military|army|navy|air force|marines|pentagon|defense|defence|missile|weapon|troops|soldier|warship|fighter jet|drone)\b",
    "entertainment": r"\b(movie|film|tv|television|series|actor|actress|celebrity|music|album|song|singer|concert|hollywood|award|streaming|box office)\b",
}


def norm_source(value: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    if raw.startswith("the") and len(raw) > 6:
        raw2 = raw[3:]
        if raw2 in ALIASES: raw = raw2
    return ALIASES.get(raw, raw or "unknown")


def field(item, name):
    return (item.findtext(name) or "").strip()


def headline(item):
    t = field(item, "title")
    src = field(item, "source")
    suffixes = [f" - {src}", f" — {src}"] if src else []
    for suffix in suffixes:
        if t.lower().endswith(suffix.lower()):
            return t[:-len(suffix)].strip()
    return t


def content_text(item):
    names = ("description", "summary", "contentBrief", "content_brief", "whyMatters", "why_matters", "context", "paraphrase")
    chunks = []
    for n in names:
        v = field(item, n)
        if v: chunks.append(v)
    # Include nested related/coverage text only as a modest richness signal.
    for child in item:
        tag = child.tag.lower()
        if "summary" in tag or "brief" in tag or "context" in tag:
            if child.text and child.text.strip(): chunks.append(child.text.strip())
    return " ".join(chunks)


def parse_dt(item):
    for n in ("pubDate", "published", "date"):
        v = field(item, n)
        if not v: continue
        try:
            if "T" in v:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            else:
                dt = parsedate_to_datetime(v)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return datetime(1970,1,1,tzinfo=timezone.utc)


def title_tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w)>2 and w not in STOP]


def title_key(text):
    return " ".join(title_tokens(text))


def canonical_url(url):
    if not url: return ""
    url = re.sub(r"([?&])(utm_[^=&]+|fbclid|gclid|mc_[^=&]+)=[^&#]*", "", url, flags=re.I)
    url = re.sub(r"[?&]+$", "", url)
    return url.rstrip("/")


def informative_title_score(text):
    toks = title_tokens(text)
    score = min(18.0, len(toks) * 1.7)
    if re.search(r"\b\d[\d,.$%:-]*\b", text): score += 2
    if len(text) >= 55: score += 3
    if VAGUE.search(text): score -= 8
    return max(0.0, score)


def content_score(item):
    text = content_text(item)
    n = len(text)
    if n >= 500: return 22.0
    if n >= 300: return 18.0
    if n >= 180: return 14.0
    if n >= 100: return 9.0
    if n >= 50: return 5.0
    return 0.0


def category_score(item, cat):
    pat = CATEGORY_ANCHORS.get(cat)
    if not pat: return 0.0
    hay = headline(item) + " " + content_text(item)[:600]
    hits = len(re.findall(pat, hay, re.I))
    return min(14.0, hits * 4.0)


def freshness_score(item, newest):
    dt = parse_dt(item)
    age_h = max(0.0, (newest - dt).total_seconds() / 3600.0)
    # 14-day feed: freshness matters, but does not erase a high-impact older story.
    return max(0.0, 18.0 * (1.0 - age_h / (14.0*24.0)))


def source_rank_map(cat):
    out = {}
    for idx, name in enumerate(HIERARCHIES.get(cat, []), 1):
        out[norm_source(name)] = idx
    return out


def source_rank(item, cat):
    ranks = source_rank_map(cat)
    return ranks.get(norm_source(field(item,"source")), 1000)


def editorial_score(item, cat, newest):
    sr = source_rank(item, cat)
    named_bonus = 18.0 if sr < 1000 else 5.0
    rank_bonus = max(0.0, 12.0 - (sr-1)*0.55) if sr < 1000 else 0.0
    return (
        informative_title_score(headline(item))
        + content_score(item)
        + category_score(item, cat)
        + freshness_score(item, newest)
        + named_bonus + rank_bonus
    )


def content_sufficient(item):
    h = headline(item).strip()
    body = content_text(item)
    toks = title_tokens(h)
    vague = bool(VAGUE.search(h))
    short = len(toks) < 5 or len(h) < 34
    # A terse or vague publisher headline is allowed when our paraphrased/context
    # content actually explains the event.
    if (short or vague) and len(body) < 140:
        return False, "short-vague-without-content"
    if len(toks) < 3 and len(body) < 220:
        return False, "non-informative-headline"
    return True, ""


def near_duplicate(a, b):
    ta, tb = title_key(headline(a)), title_key(headline(b))
    if not ta or not tb: return False
    if ta == tb: return True
    sa, sb = set(ta.split()), set(tb.split())
    overlap = len(sa & sb) / max(1, min(len(sa),len(sb)))
    seq = SequenceMatcher(None, ta, tb).ratio()
    # Deliberately strong threshold: collapse copies/syndication, not distinct
    # coverage of the same broad event.
    return (overlap >= .82 and seq >= .78) or seq >= .91


def dedupe(rows, cat, newest):
    ranked = sorted(rows, key=lambda x:(editorial_score(x,cat,newest), parse_dt(x)), reverse=True)
    kept=[]; removed=[]; seen_urls=set()
    for item in ranked:
        u = canonical_url(field(item,"link"))
        if u and u in seen_urls:
            removed.append((item,"exact-url")); continue
        dup = next((k for k in kept if near_duplicate(item,k)), None)
        if dup is not None:
            removed.append((item,"near-duplicate")); continue
        kept.append(item)
        if u: seen_urls.add(u)
    return kept, removed


def add_meta(item, name, value):
    node=item.find(name)
    if node is None: node=ET.SubElement(item,name)
    node.text=str(value)


def ladder(rows, cat):
    if not rows: return [], [], []
    newest=max(parse_dt(x) for x in rows)
    eligible=[]; rejected=[]
    for item in rows:
        ok,reason=content_sufficient(item)
        if ok: eligible.append(item)
        else: rejected.append((item,reason))
    eligible,dupes=dedupe(eligible,cat,newest)
    rejected.extend(dupes)

    ranks=source_rank_map(cat)
    buckets=defaultdict(list)
    for item in eligible:
        buckets[norm_source(field(item,"source"))].append(item)
    for sid,b in buckets.items():
        b.sort(key=lambda x:(editorial_score(x,cat,newest),parse_dt(x)), reverse=True)
        for i,item in enumerate(b,1):
            add_meta(item,"v52SourceRank",ranks.get(sid,1000))
            add_meta(item,"v52ArticleRank",i)
            add_meta(item,"v52ArticleScore",f"{editorial_score(item,cat,newest):.2f}")

    named=[sid for sid,_ in sorted(ranks.items(), key=lambda kv:kv[1]) if sid in buckets]
    fallback=[sid for sid in buckets if sid not in ranks]
    # Backup publishers are ordered by their strongest story, but remain distinct
    # publisher turns rather than one monolithic "Google" bucket.
    fallback.sort(key=lambda sid: editorial_score(buckets[sid][0],cat,newest), reverse=True)
    source_order=named+fallback

    out=[]; round_no=1
    while True:
        added=0
        for sid in source_order:
            b=buckets[sid]
            if len(b) >= round_no:
                item=b[round_no-1]
                add_meta(item,"v52SelectionRound",round_no)
                add_meta(item,"v52SelectionMethod","named-source" if sid in ranks else "fallback-source")
                out.append(item); added+=1
        if not added: break
        round_no+=1
    return out,rejected,source_order


def main():
    tree=ET.parse(NEWS); channel=tree.getroot().find("channel")
    if channel is None: raise SystemExit("RSS channel missing")
    original=list(channel.findall("item"))
    by=defaultdict(list); cat_order=[]
    for item in original:
        cat=field(item,"category").lower()
        if cat not in cat_order: cat_order.append(cat)
        by[cat].append(item)

    report={"tabs":{},"excluded":["underreported"],"model":"per-tab-source-ladder-b2"}
    final_by={}
    for cat,rows in by.items():
        if cat not in HIERARCHIES or cat=="underreported":
            final_by[cat]=rows; continue
        ordered,rejected,sources=ladder(rows,cat)
        final_by[cat]=ordered
        before=Counter(norm_source(field(x,"source")) for x in rows)
        after=Counter(norm_source(field(x,"source")) for x in ordered)
        report["tabs"][cat]={
            "before":len(rows),"after":len(ordered),"removed":len(rejected),
            "namedHierarchySize":len(HIERARCHIES[cat]),"activeSources":len(sources),
            "sourceOrder":sources[:30],
            "topCounts":after.most_common(8),
            "removedReasons":dict(Counter(r for _,r in rejected)),
            "round1Count":sum(1 for x in ordered if field(x,"v52SelectionRound")=="1"),
        }

    for item in list(channel.findall("item")): channel.remove(item)
    for cat in cat_order:
        for item in final_by.get(cat,[]): channel.append(item)
    tree.write(NEWS,encoding="utf-8",xml_declaration=True)
    REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
