#!/usr/bin/env python3
"""Central V5.1 editorial/category policy.

Keeps tab priorities, legal overlap, and article-type expectations in one place so
routing, dedupe, and validation do not drift independently.
"""
from __future__ import annotations

ROUTABLE = {'world','us','presidential','federal','nm','local','region','technology','gaming','military','nfl'}
PRIORITY = {'local':90,'nm':85,'presidential':82,'federal':80,'nfl':80,'gaming':76,'technology':74,'military':72,'region':68,'us':55,'world':50}

# Symmetric allowed-overlap pairs. These may describe the same event without being a leak.
ALLOWED_OVERLAP = {
    frozenset(('presidential','federal')),
    frozenset(('world','military')),
    frozenset(('nm','local')),
    frozenset(('nm','region')),
    frozenset(('local','region')),
    frozenset(('technology','gaming')),
}

ARTICLE_TYPE_POLICY = {
    'gaming': {'allow': {'news','analysis'}, 'deny': {'review','guide','listicle'}},
    'technology': {'allow': {'news','analysis'}, 'deny': {'review','guide','listicle'}},
    'world': {'allow': {'news','analysis'}, 'deny': set()},
    'us': {'allow': {'news','analysis'}, 'deny': set()},
}

# Collection lanes are configuration only; they let workflows separate urgent and expensive passes.
FAST_LANE = {'top','world','us','presidential','federal','military','nfl','technology'}
SLOW_LANE = {'legislation','nm','local','region','gaming','underreported','entertainment','x','boxoffice'}

def overlap_allowed(a: str, b: str) -> bool:
    return a == b or frozenset((a,b)) in ALLOWED_OVERLAP
