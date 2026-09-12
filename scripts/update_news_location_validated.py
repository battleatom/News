#!/usr/bin/env python3
"""Location validation layer for the normalized collector.

The nationwide inventory remains broad so any user can receive location-aware
coverage, but Local and Region cards must prove their geography before they enter
that inventory. The browser then filters Region to the user's detected region.
"""
from __future__ import annotations

import re

import update_news_normalized as normalized

core = normalized.core

# Map generic Region search queries to the geography they are allowed to populate.
REGION_QUERY_META = {}
for region_name, queries in core.QUERIES.get("region", {}).items():
    for query in queries:
        state = core.region_query_state(query)
        if state:
            REGION_QUERY_META[str(query)] = {"state": state, "region": region_name}

STATE_NAMES = tuple(sorted(core.US_STATE_NAMES, key=len, reverse=True))
STATE_ABBREVIATIONS = {
    "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO",
    "Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID",
    "Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA",
    "Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN",
    "Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV",
    "New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC",
    "North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA",
    "Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX",
    "Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV",
    "Wisconsin":"WI","Wyoming":"WY"
}

SOURCE_STATES = {}
for market in normalized.NEWS_MARKETS:
    state = market.get("stateName", "")
    for src in market.get("sources", []):
        token = normalized.source_token(src)
        if token:
            SOURCE_STATES.setdefault(token, set()).add(state)

_original_fetch = core.fetch
_original_parse_items = core.parse_items


def _raw_text(item):
    return f"{item.get('title','')} {item.get('description','')} {item.get('source','')}"


def _mentions_state(raw, state_name):
    if not state_name:
        return False
    if re.search(rf"\b{re.escape(state_name)}\b", raw, flags=re.I):
        return True
    abbr = STATE_ABBREVIATIONS.get(state_name, "")
    return bool(abbr and re.search(rf"\b{re.escape(abbr)}\b", raw))


def _other_state_mentions(raw, expected_state):
    hits = []
    for state in STATE_NAMES:
        if state == expected_state:
            continue
        if re.search(rf"\b{re.escape(state)}\b", raw, flags=re.I):
            hits.append(state)
    return hits


def _source_supports_state(item, state_name):
    token = normalized.source_token(item.get("source") or "")
    states = SOURCE_STATES.get(token, set())
    return bool(state_name and len(states) == 1 and state_name in states)


def strict_local_story_relevant(item, market):
    """A Local card must prove the market, not merely the state.

    Direct city mention is strongest. A newsroom explicitly assigned to exactly one
    market is also accepted unless the story clearly names a different state.
    State-name-only matches from generic search results are rejected.
    """
    raw = _raw_text(item)
    city = str(market.get("city") or "").strip()
    state = str(market.get("stateName") or "").strip()
    if city and re.search(rf"\b{re.escape(city)}\b", raw, flags=re.I):
        return True

    source = normalized.source_token(item.get("source") or "")
    approved_sources = {normalized.source_token(x) for x in market.get("sources", [])}
    if source and source in approved_sources:
        if _other_state_mentions(raw, state):
            return False
        return True

    return False


def strict_region_story_relevant(item, state_name):
    """A Region card must prove the state represented by its collector query."""
    raw = _raw_text(item)
    if _mentions_state(raw, state_name):
        return True
    if _source_supports_state(item, state_name) and not _other_state_mentions(raw, state_name):
        return True
    return False


def validated_fetch(query):
    root = _original_fetch(query)
    meta = REGION_QUERY_META.get(str(query))
    if meta:
        root.set("underreportedExpectedState", meta["state"])
        root.set("underreportedExpectedRegion", meta["region"])
    return root


def validated_parse_items(root, category, source_override=None):
    items = _original_parse_items(root, category, source_override=source_override)

    if category == "local":
        kept = []
        for item in items:
            market = normalized.MARKET_BY_ID.get(item.get("marketId", ""))
            if market is None:
                # Legacy untagged Local items are not trusted into the nationwide bank.
                continue
            if strict_local_story_relevant(item, market):
                kept.append(item)
        return kept

    if category == "region":
        expected_state = root.get("underreportedExpectedState", "")
        expected_region = root.get("underreportedExpectedRegion", "")
        if not expected_state:
            return []
        kept = []
        for item in items:
            if not strict_region_story_relevant(item, expected_state):
                continue
            item["state"] = expected_state
            if expected_region:
                item["region"] = expected_region
            kept.append(item)
        return kept

    return items


core.fetch = validated_fetch
core.parse_items = validated_parse_items


def main():
    normalized.main()


if __name__ == "__main__":
    main()
