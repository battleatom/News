#!/usr/bin/env python3
"""Normalized production collector wrapper with nationwide location-aware Local coverage.

The market database is the single source of truth for Local collection and browser
routing. Each active market keeps a small bounded story bank so rural users can fall
back to the nearest newsroom without one part of the country crowding out another.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
from pathlib import Path

import update_news as core

ROOT = Path(__file__).resolve().parents[1]
MARKET_MANIFEST = ROOT / "data" / "us_news_markets.json"
LOCAL_STORIES_PER_MARKET = 4


def load_markets():
    manifest = json.loads(MARKET_MANIFEST.read_text(encoding="utf-8"))
    markets = []
    for rel in manifest.get("files", []):
        payload = json.loads((MARKET_MANIFEST.parent / rel).read_text(encoding="utf-8"))
        markets.extend(payload.get("markets", []))
    ids = [m.get("id") for m in markets]
    if not markets or len(ids) != len(set(ids)):
        raise RuntimeError("News-market database is empty or contains duplicate market IDs")
    return markets


NEWS_MARKETS = load_markets()
MARKET_BY_QUERY = {m["query"]: m for m in NEWS_MARKETS}
MARKET_BY_ID = {m["id"]: m for m in NEWS_MARKETS}

POOL_POLICY = {
    "world": (30, 35, 40), "us": (30, 35, 40), "presidential": (30, 35, 40),
    "federal": (30, 35, 40), "nm": (30, 35, 40), "region": (30, 35, 80),
    "nfl": (30, 35, 40), "technology": (30, 35, 40), "gaming": (30, 35, 40),
    "military": (30, 35, 40), "local": (8, LOCAL_STORIES_PER_MARKET * len(NEWS_MARKETS), LOCAL_STORIES_PER_MARKET * len(NEWS_MARKETS)),
}

core.MAX_AGE_HOURS = 96
core.CATEGORY_POOL_MINIMUMS = {cat: policy[0] for cat, policy in POOL_POLICY.items()}
core.LOCAL_QUERIES = [m["query"] for m in NEWS_MARKETS]
core.QUERIES["local"] = list(core.LOCAL_QUERIES)


def source_token(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


market_sources = {source_token(src) for m in NEWS_MARKETS for src in m.get("sources", []) if source_token(src)}
core.TRUSTED_LOCAL_SOURCE_TOKENS = tuple(sorted(set(core.TRUSTED_LOCAL_SOURCE_TOKENS) | market_sources))
core.TRUSTED_SOURCE_TOKENS = tuple(sorted(set(core.TRUSTED_SOURCE_TOKENS) | market_sources))


def expanded_feed_url(query):
    q = urllib.parse.quote(f"{query} when:4d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


core.feed_url = expanded_feed_url

# Retain existing replenishment sources for non-location tabs.
core.TRUSTED_CATEGORY_FALLBACKS.update({
    "world": [("Reuters", "site:reuters.com world international breaking news"), ("Associated Press", "site:apnews.com world international breaking news"), ("BBC", "site:bbc.com/news world international"), ("NPR", "site:npr.org world international")],
    "us": [("Reuters", "site:reuters.com United States US politics national news"), ("Associated Press", "site:apnews.com United States US politics national news"), ("NPR", "site:npr.org United States national politics"), ("USA Today", "site:usatoday.com United States national news")],
    "nm": [("Source New Mexico", "site:sourcenm.com New Mexico news government health education environment"), ("New Mexico In Depth", "site:nmindepth.com New Mexico news government education health"), ("Albuquerque Journal", "site:abqjournal.com New Mexico news"), ("Santa Fe New Mexican", "site:santafenewmexican.com New Mexico news")],
    "military": [("Defense News", "site:defensenews.com Pentagon US military defense"), ("Military Times", "site:militarytimes.com US military Pentagon troops"), ("Breaking Defense", "site:breakingdefense.com Pentagon military defense"), ("Stars and Stripes", "site:stripes.com US military troops Pentagon"), ("Reuters", "site:reuters.com US military Pentagon defense")],
})

_original_fetch = core.fetch
_original_parse_items = core.parse_items
_original_select_category = core.select_category_stories
_original_select_region = core.select_region_stories
_region_total = 0


def market_fetch(query):
    root = _original_fetch(query)
    market = MARKET_BY_QUERY.get(str(query))
    if market is not None:
        root.set("underreportedMarketId", market["id"])
    return root


def local_story_relevant(item, market):
    text = f"{item.get('title','')} {item.get('description','')}".lower()
    city = market.get("city", "").lower()
    state_name = market.get("stateName", "").lower()
    state_code = market.get("state", "").lower()
    if city and city in text:
        return True
    if state_name and state_name in text:
        return True
    # State abbreviations are accepted only as bounded uppercase-style tokens in source text.
    raw = f"{item.get('title','')} {item.get('description','')}"
    if state_code and re.search(rf"\b{re.escape(market['state'])}\b", raw):
        return True
    return False


def market_parse_items(root, category, source_override=None):
    items = _original_parse_items(root, category, source_override=source_override)
    market = MARKET_BY_ID.get(root.get("underreportedMarketId", ""))
    if category != "local" or market is None:
        return items
    enriched = []
    for item in items:
        if not local_story_relevant(item, market):
            continue
        item.update({
            "marketId": market["id"], "marketCity": market["city"], "marketState": market["state"],
            "state": market["stateName"], "region": market["region"],
            "latitude": str(market["lat"]), "longitude": str(market["lon"]),
        })
        enriched.append(item)
    return enriched


core.fetch = market_fetch
core.parse_items = market_parse_items


def select_local_market_bank(items):
    groups = {}
    legacy = []
    for item in items:
        market_id = item.get("marketId")
        if market_id:
            groups.setdefault(market_id, []).append(item)
        else:
            legacy.append(item)
    selected = []
    seen = set()
    for market in NEWS_MARKETS:
        ranked = sorted(groups.get(market["id"], []), key=lambda x: x["published"], reverse=True)
        source_seen = set()
        market_selected = []
        for item in ranked:
            k = core.key(item); src = core.source_key(item.get("source") or "Unknown")
            if not k or k in seen or src in source_seen:
                continue
            market_selected.append(item); seen.add(k); source_seen.add(src)
            if len(market_selected) >= LOCAL_STORIES_PER_MARKET:
                break
        if len(market_selected) < LOCAL_STORIES_PER_MARKET:
            for item in ranked:
                k = core.key(item)
                if not k or k in seen:
                    continue
                market_selected.append(item); seen.add(k)
                if len(market_selected) >= LOCAL_STORIES_PER_MARKET:
                    break
        selected.extend(market_selected)
    # Preserve a small compatibility tail for currently untagged legacy Local records.
    for item in sorted(legacy, key=lambda x: x["published"], reverse=True):
        k = core.key(item)
        if k and k not in seen:
            selected.append(item); seen.add(k)
        if len([x for x in selected if not x.get("marketId")]) >= 20:
            break
    return selected


def normalized_select_category(items, limit=None):
    category = items[0].get("category") if items else ""
    if category == "legislation":
        return []
    if category == "local":
        return select_local_market_bank(items)
    _minimum, target, hard_max = POOL_POLICY.get(category, (30, 35, 40))
    requested = target if limit is None else min(int(limit), hard_max)
    return _original_select_category(items, limit=requested)


def normalized_select_region(items, per_state=8, limit=80):
    global _region_total
    hard_max = POOL_POLICY["region"][2]
    remaining = max(0, hard_max - _region_total)
    if not items or remaining == 0:
        return []
    bucket_cap = min(10, remaining)
    chosen = _original_select_region(items, per_state=per_state, limit=bucket_cap)
    _region_total += len(chosen)
    return chosen


core.select_category_stories = normalized_select_category
core.select_region_stories = normalized_select_region


def normalized_build(items):
    now = core.datetime.now(core.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    esc = lambda v: html.escape(str(v or ""), quote=False)
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>', '<title>Underreported News Brief</title>', '<link>https://battleatom.github.io/News/</link>', '<description>High-impact stories outside the usual news cycle</description>', f'<lastBuildDate>{now}</lastBuildDate>']
    for item in items:
        guid = core.hashlib.sha1((item["link"] + "|" + item["category"]).encode("utf-8")).hexdigest()
        out += ["<item>", f'<title>{esc(item["title"])}</title>', f'<link>{esc(item["link"])}</link>', f'<description>{esc(item.get("description", ""))}</description>', f'<pubDate>{esc(item["pubDate"])}</pubDate>', f'<source>{esc(item["source"])}</source>', f'<category>{esc(item["category"])}</category>', f'<region>{esc(item.get("region", ""))}</region>', f'<state>{esc(item.get("state", ""))}</state>', f'<marketId>{esc(item.get("marketId", ""))}</marketId>', f'<marketCity>{esc(item.get("marketCity", ""))}</marketCity>', f'<marketState>{esc(item.get("marketState", ""))}</marketState>', f'<latitude>{esc(item.get("latitude", ""))}</latitude>', f'<longitude>{esc(item.get("longitude", ""))}</longitude>', f'<whyMatters>{esc(item.get("whyMatters", ""))}</whyMatters>']
        related = item.get('_relatedArticles', [])
        if related:
            out.append('<relatedArticles>')
            for rel in related:
                out += [f'<article><title>{esc(rel.get("title",""))}</title>', f'<link>{esc(rel.get("link",""))}</link>', f'<source>{esc(rel.get("source",""))}</source></article>']
            out.append('</relatedArticles>')
        out += [f'<guid isPermaLink="false">{guid}</guid>', "</item>"]
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


core.build = normalized_build


def main():
    global _region_total
    _region_total = 0
    print(f"Loaded {len(NEWS_MARKETS)} U.S. news markets; Local bank cap {LOCAL_STORIES_PER_MARKET} stories/market")
    core.main()


if __name__ == "__main__":
    main()
