#!/usr/bin/env python3
"""V4 collector entrypoint.

Adds a verified Entertainment tab on top of the normalized nationwide collector.
Editorial policy:
- first five Entertainment cards are the newest verified stories
- remaining cards prioritize credible specialist entertainment reporting that is
  less likely to dominate mainstream national coverage
- Entertainment cards that overlap an Underreported event receive explicit
  cross-links in the generated RSS for the UI to highlight in red
"""
from __future__ import annotations

import html
import re

import update_news_normalized as normalized

core = normalized.core

ENTERTAINMENT_LIMIT = 25
ENTERTAINMENT_NEWEST = 5
ENTERTAINMENT_SPECIALIST_SOURCES = (
    "variety", "billboard", "rolling stone", "deadline", "hollywood reporter",
    "entertainment weekly", "people", "pitchfork", "vulture",
)
ENTERTAINMENT_REJECT_TERMS = (
    "horoscope", "astrology", "best dressed", "worst dressed", "bikini",
    "spotted with", "dating rumor", "dating rumours", "lookalike", "fan theory",
)
ENTERTAINMENT_TERMS = (
    "actor", "actress", "singer", "rapper", "musician", "artist", "band",
    "director", "filmmaker", "producer", "comedian", "performer", "celebrity",
    "hollywood", "film", "movie", "television", "tv", "series", "album",
    "song", "single", "tour", "concert", "music", "entertainment", "award",
    "grammy", "emmy", "oscar", "screen actors guild", "sag-aftra",
)

if "entertainment" not in core.SECTIONS:
    insert_at = core.SECTIONS.index("world") if "world" in core.SECTIONS else 2
    core.SECTIONS.insert(insert_at, "entertainment")

core.QUERIES["entertainment"] = [
    "actors actresses Hollywood film television entertainment news",
    "music artists singers musicians album tour concert entertainment news",
    "actor actress lawsuit health death interview entertainment industry",
    "music artist lawsuit award contract tour entertainment industry",
    "Hollywood actor actress director producer entertainment industry news",
]

_entertainment_sources = (
    "variety", "billboard", "rolling stone", "deadline", "hollywood reporter",
    "entertainment weekly", "people", "pitchfork", "vulture",
)
core.TRUSTED_SOURCE_TOKENS = tuple(sorted(set(core.TRUSTED_SOURCE_TOKENS) | set(_entertainment_sources)))
core.CATEGORY_POOL_MINIMUMS["entertainment"] = 20
normalized.POOL_POLICY["entertainment"] = (20, ENTERTAINMENT_LIMIT, 30)
core.TRUSTED_CATEGORY_FALLBACKS["entertainment"] = [
    ("Variety", "site:variety.com actor actress Hollywood television film entertainment"),
    ("Billboard", "site:billboard.com music artist singer rapper tour album"),
    ("Rolling Stone", "site:rollingstone.com music artist actor entertainment"),
    ("Deadline", "site:deadline.com actor actress television film Hollywood"),
    ("The Hollywood Reporter", "site:hollywoodreporter.com actor actress film television entertainment"),
    ("Entertainment Weekly", "site:ew.com actor actress music television film entertainment"),
]

_original_select = core.select_category_stories


def _source_key(item):
    return core.source_key(item.get("source") or "")


def _entertainment_relevant(item):
    text = f"{item.get('title','')} {item.get('description','')}".lower()
    if any(term in text for term in ENTERTAINMENT_REJECT_TERMS):
        return False
    return any(term in text for term in ENTERTAINMENT_TERMS)


def _specialist(item):
    source = (item.get("source") or "").lower()
    return any(token in source for token in ENTERTAINMENT_SPECIALIST_SOURCES)


def _ent_title_terms(item):
    stop = {
        "the","a","an","and","or","but","for","from","with","into","over","after","before",
        "about","amid","during","this","that","new","news","latest","says","said","actor",
        "actress","film","movie","music","artist","singer","series","television","tv",
        "entertainment","hollywood","project",
    }
    return {w for w in re.findall(r"[a-z0-9]+", (item.get("title") or "").lower()) if len(w) >= 3 and w not in stop}


def _same_entertainment_event(a, b):
    ta, tb = _ent_title_terms(a), _ent_title_terms(b)
    if not ta or not tb:
        return False
    shared = ta & tb
    smaller = min(len(ta), len(tb))
    return smaller >= 3 and len(shared) >= 3 and len(shared) / smaller >= 0.70


def select_entertainment(items, limit=ENTERTAINMENT_LIMIT):
    items = [x for x in items if _entertainment_relevant(x)]
    ranked = sorted(items, key=lambda x: x["published"], reverse=True)
    selected = []
    seen = set()

    # Rule 1: exactly the newest verified stories lead the section.
    for item in ranked:
        k = core.key(item)
        if not k or k in seen:
            continue
        copy = dict(item)
        copy["entertainmentTier"] = "newest"
        selected.append(copy)
        seen.add(k)
        if len(selected) >= min(ENTERTAINMENT_NEWEST, limit):
            break

    # Rule 2: after the first five, prefer specialist outlets and publisher variety.
    remainder = [x for x in ranked if core.key(x) and core.key(x) not in seen]
    remainder.sort(key=lambda x: (_specialist(x), x["published"]), reverse=True)
    source_counts = {}
    for item in remainder:
        k = core.key(item)
        src = _source_key(item)
        if not k or k in seen or source_counts.get(src, 0) >= 3:
            continue
        if any(_same_entertainment_event(prior, item) for prior in selected):
            continue
        copy = dict(item)
        copy["entertainmentTier"] = "under-the-radar"
        selected.append(copy)
        seen.add(k)
        source_counts[src] = source_counts.get(src, 0) + 1
        if len(selected) >= limit:
            break

    return selected


def v4_select_category(items, limit=None):
    category = items[0].get("category") if items else ""
    if category == "entertainment":
        requested = ENTERTAINMENT_LIMIT if limit is None else min(int(limit), ENTERTAINMENT_LIMIT)
        return select_entertainment(items, requested)
    return _original_select(items, limit=limit)


core.select_category_stories = v4_select_category


def _entity_phrases(item):
    raw = item.get("title") or ""
    phrases = re.findall(r"\b(?:[A-Z][a-zA-Z'’.-]+)(?:\s+(?:[A-Z][a-zA-Z'’.-]+)){1,3}\b", raw)
    noise = {"United States", "New York", "Los Angeles", "White House", "Associated Press"}
    return {p.strip().lower() for p in phrases if p.strip() not in noise}


def _article_terms(item):
    return core.article_terms(item) if hasattr(core, "article_terms") else set(re.findall(r"[a-z0-9]{4,}", f"{item.get('title','')} {item.get('description','')}".lower()))


def _related_to_underreported(ent, under):
    if core.same_event_topic(ent, under):
        return True
    entities = _entity_phrases(ent) & _entity_phrases(under)
    if not entities:
        return False
    shared = _article_terms(ent) & _article_terms(under)
    return len(shared) >= 2


def _attach_underreported_links(items):
    entertainment = [x for x in items if x.get("category") == "entertainment"]
    underreported = [x for x in items if x.get("category") == "underreported"]
    for ent in entertainment:
        links = []
        for under in underreported:
            if _related_to_underreported(ent, under):
                links.append({
                    "title": under.get("title", ""),
                    "link": under.get("link", ""),
                    "source": under.get("source", ""),
                })
            if len(links) >= 2:
                break
        if links:
            ent["_underreportedLinks"] = links


def v4_build(items):
    _attach_underreported_links(items)
    now = core.datetime.now(core.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    esc = lambda v: html.escape(str(v or ""), quote=False)
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>', '<title>Underreported News Brief</title>', '<link>https://battleatom.github.io/News/</link>', '<description>High-impact stories outside the usual news cycle</description>', f'<lastBuildDate>{now}</lastBuildDate>']
    for item in items:
        guid = core.hashlib.sha1((item["link"] + "|" + item["category"]).encode("utf-8")).hexdigest()
        out += ["<item>", f'<title>{esc(item["title"])}</title>', f'<link>{esc(item["link"])}</link>', f'<description>{esc(item.get("description", ""))}</description>', f'<pubDate>{esc(item["pubDate"])}</pubDate>', f'<source>{esc(item["source"])}</source>', f'<category>{esc(item["category"])}</category>', f'<region>{esc(item.get("region", ""))}</region>', f'<state>{esc(item.get("state", ""))}</state>', f'<marketId>{esc(item.get("marketId", ""))}</marketId>', f'<marketCity>{esc(item.get("marketCity", ""))}</marketCity>', f'<marketState>{esc(item.get("marketState", ""))}</marketState>', f'<latitude>{esc(item.get("latitude", ""))}</latitude>', f'<longitude>{esc(item.get("longitude", ""))}</longitude>', f'<entertainmentTier>{esc(item.get("entertainmentTier", ""))}</entertainmentTier>', f'<whyMatters>{esc(item.get("whyMatters", ""))}</whyMatters>']
        related = item.get('_relatedArticles', [])
        if related:
            out.append('<relatedArticles>')
            for rel in related:
                out += [f'<article><title>{esc(rel.get("title",""))}</title>', f'<link>{esc(rel.get("link",""))}</link>', f'<source>{esc(rel.get("source",""))}</source></article>']
            out.append('</relatedArticles>')
        under_links = item.get('_underreportedLinks', [])
        if under_links:
            out.append('<underreportedLinks>')
            for rel in under_links:
                out += [f'<article><title>{esc(rel.get("title",""))}</title>', f'<link>{esc(rel.get("link",""))}</link>', f'<source>{esc(rel.get("source",""))}</source></article>']
            out.append('</underreportedLinks>')
        out += [f'<guid isPermaLink="false">{guid}</guid>', "</item>"]
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


core.build = v4_build


def main():
    print("V4 Entertainment enabled: newest 5 + verified under-the-radar coverage + Underreported cross-links")
    normalized.main()


if __name__ == "__main__":
    main()
