#!/usr/bin/env python3
"""V5.3 quality-lab collector wrapper.

This branch is intentionally isolated from production and validated V5.2.
It expands source discovery without changing the V5.2 UX or release branches.
"""
from __future__ import annotations

import update_news_v52 as v52

core = v52.core

WORLD_SOURCE_EXPANSION = [
    ("BBC", "site:bbc.com/news/world international breaking politics conflict election economy"),
    ("Al Jazeera", "site:aljazeera.com/news international world politics conflict election economy"),
    ("The Guardian", "site:theguardian.com/world international politics conflict election economy"),
    ("France 24", "site:france24.com/en international world politics conflict election"),
    ("Deutsche Welle", "site:dw.com/en world international politics conflict election"),
    ("CBC", "site:cbc.ca/news/world international world politics conflict election"),
    ("NHK", "site:nhk.or.jp/nhkworld world international Asia politics economy"),
    ("The Hindu", "site:thehindu.com/news/international world Asia politics conflict"),
    ("South China Morning Post", "site:scmp.com/news/world international Asia politics economy"),
    ("The Times of India", "site:timesofindia.indiatimes.com/world international politics conflict"),
    ("The Kyiv Independent", "site:kyivindependent.com Ukraine Europe war diplomacy"),
    ("Haaretz", "site:haaretz.com Israel Middle East politics conflict"),
]

NFL_SOURCE_EXPANSION = [
    ("NFL.com", "site:nfl.com/news NFL injury trade roster game coach quarterback"),
    ("CBS Sports", "site:cbssports.com/nfl NFL injury trade roster game coach quarterback"),
    ("NBC Sports", "site:nbcsports.com/nfl NFL injury trade roster game coach quarterback"),
    ("Fox Sports", "site:foxsports.com/nfl NFL injury trade roster game coach quarterback"),
    ("Yahoo Sports", "site:sports.yahoo.com/nfl NFL injury trade roster game coach quarterback"),
    ("ProFootballTalk", "site:nbcsports.com/nfl/profootballtalk NFL injury trade roster coach"),
    ("USA Today", "site:usatoday.com/sports/nfl NFL injury trade roster game coach"),
    ("The Athletic", "site:nytimes.com/athletic/nfl NFL injury trade roster game coach"),
]


def _extend_fallback(category: str, additions):
    table = getattr(core, "TRUSTED_CATEGORY_FALLBACKS", None)
    if not isinstance(table, dict):
        return
    rows = table.setdefault(category, [])
    seen = {(str(name).lower(), str(query).lower()) for name, query in rows}
    for name, query in additions:
        key = (name.lower(), query.lower())
        if key not in seen:
            rows.append((name, query))
            seen.add(key)


def main():
    _extend_fallback("world", WORLD_SOURCE_EXPANSION)
    _extend_fallback("nfl", NFL_SOURCE_EXPANSION)
    print(f"V5.3 source expansion: world +{len(WORLD_SOURCE_EXPANSION)}, nfl +{len(NFL_SOURCE_EXPANSION)} discovery queries")
    v52.main()


if __name__ == "__main__":
    main()
