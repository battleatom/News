#!/usr/bin/env python3
"""V4 final verification wrapper.

Loads the V4 collector policy so Entertainment and curated specialist sources are
trusted, keeps specialist-refined surfaces from being second-guessed by the legacy
generic classifier, tops up the U.S. national pool with tightly scoped domestic
coverage, finalizes verified Entertainment GUIDs and Underreported cross-links, and
applies the conservative cross-tab duplicate guard.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import classify_live_feed as classifier
import refine_tech_gaming as specialist
import update_news_v4 as v4

_base_source_is_trusted = v4.core.source_is_trusted
_base_classify = classifier.classify
_SPECIALIST_SOURCES = tuple(dict.fromkeys(
    specialist.TECH_TRUSTED + specialist.GAMING_TRUSTED + specialist.US_TRUSTED
))
_US_BACKFILL_QUERIES = [
    'United States economy inflation jobs labor national news',
    'United States housing mortgage rent consumers national news',
    'United States healthcare public health insurance national news',
    'United States schools education student debt national news',
    'United States infrastructure transportation airlines national news',
    'United States public safety crime national news',
    'United States wildfire hurricane flooding national news',
    'United States consumer prices retail household costs national news',
    'United States workers wages employment national news',
]
_US_SCOPE = re.compile(
    r'\b(united states|u\.?s\.?|americans?|american households?|american workers?|nationwide|nationally|'
    r'across the country|across the u\.?s\.?|multiple states|states across|countrywide)\b', re.I)
_US_DOMESTIC_TOPIC = re.compile(
    r'\b(economy|economic|inflation|jobs?|labor|employment|unemployment|wages?|housing|mortgages?|rent|'
    r'health care|healthcare|public health|education|schools?|student debt|crime|public safety|transportation|'
    r'airlines?|air travel|infrastructure|wildfires?|hurricanes?|flood(?:ing)?|consumers?|consumer prices?|'
    r'household costs?|retail|insurance|energy prices?)\b', re.I)


def v4_source_is_trusted(source):
    """Use production trust plus sources explicitly curated by specialist refiners."""
    value = re.sub(r"[^a-z0-9]+", " ", (source or "").lower()).strip()
    tokens = set(value.split())
    if tokens & {"xbiz", "avn"}:
        return True
    if any(name in value for name in _SPECIALIST_SOURCES):
        return True
    return _base_source_is_trusted(source)


def _set_category(item, value):
    node = item.find('category')
    if node is None:
        node = ET.SubElement(item, 'category')
    node.text = value


def _us_backfill_allowed(item):
    title = specialist.text(item, 'title')
    desc = specialist.text(item, 'description')
    raw = f'{title} {desc}'
    if specialist.LOW_VALUE_GENERAL.search(raw):
        return False
    if specialist.PRESIDENTIAL_ROUTE.search(title) or specialist.FEDERAL_ROUTE.search(title):
        return False
    if specialist.FOREIGN_US_FALSE_POSITIVE.search(title) and not _US_SCOPE.search(title):
        return False
    return bool(_US_SCOPE.search(raw) and _US_DOMESTIC_TOPIC.search(raw))


def _specialist_keep(item):
    """Honor a prior specialist qualification without weakening unrelated source rules."""
    current = specialist.text(item, 'category').lower()
    source = specialist.text(item, 'source')
    if not source:
        return None
    valid = False
    if current == 'technology':
        valid = specialist.tech_relevance_decision(item) == 'technology'
    elif current == 'gaming':
        valid = specialist.gaming_allowed(item)
    elif current == 'us':
        valid = specialist.us_route(item) == 'us' or _us_backfill_allowed(item)
    if not valid:
        return None
    return {
        'title': specialist.text(item, 'title'), 'source': source, 'current': current,
        'action': 'keep', 'reason': 'specialist-refinement-confirmed', 'category': current,
        'confidence': 1.0, 'scores': {}, 'evidence': ['specialist-refinement'],
    }


def v4_classify(item):
    specialist_decision = _specialist_keep(item)
    if specialist_decision is not None:
        return specialist_decision
    return _base_classify(item)


def augment_us_pool(path='News'):
    """Top up the already-refined U.S. tab without weakening its routing rules."""
    feed = Path(path)
    if not feed.exists():
        return
    tree = ET.parse(feed)
    channel = tree.getroot().find('channel')
    if channel is None:
        return
    current = [i for i in channel.findall('item') if specialist.text(i, 'category') == 'us']
    candidates = list(current)
    for item in specialist.fetch_google(_US_BACKFILL_QUERIES, 'us', 4):
        if not specialist.source_is(specialist.text(item, 'source'), specialist.US_TRUSTED):
            continue
        route = specialist.us_route(item)
        if route == 'us' or _us_backfill_allowed(item):
            _set_category(item, 'us')
            candidates.append(item)
    ranked = []
    for cluster in specialist.cluster_items(candidates):
        lead = max(cluster, key=lambda i: specialist.parse_date(specialist.text(i, 'pubDate')))
        coverage = len({specialist.source_family(specialist.text(i, 'source')) for i in cluster if specialist.text(i, 'source')}) or 1
        score = coverage * 90 + max(0, 96 - specialist.age_hours(lead))
        if specialist.source_is(specialist.text(lead, 'source'), specialist.US_TRUSTED):
            score += 25
        specialist.add_rank_fields(lead, 'us', score, coverage)
        ranked.append((score, specialist.parse_date(specialist.text(lead, 'pubDate')), lead))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    selected = [row[2] for row in ranked[:specialist.MAX_US]]
    if len(selected) <= len(current):
        print(f'U.S. national backfill: {len(current)}->{len(selected)}; no additional qualifying stories.')
        return
    specialist.replace_categories(channel, {'us'}, selected)
    tree.write(feed, encoding='utf-8', xml_declaration=True)
    print(f'U.S. national backfill: {len(current)}->{len(selected)} trusted domestic stories.')


classifier.source_is_trusted = v4_source_is_trusted
classifier.classify = v4_classify
# Entertainment, Technology, Gaming and U.S. are already cleaned by dedicated
# specialist passes before verification. Keep source-trust checks and dedupe here,
# but do not run a second generic category reroute over those curated pools. The
# final V5 authoritative filter still owns the last routing decision.
classifier.NON_ROUTABLE_INPUT = set(classifier.NON_ROUTABLE_INPUT) | {
    "entertainment", "technology", "gaming", "us"
}

import verify_feed

# verify_feed imported classify by name, so point it at the specialist-aware wrapper.
verify_feed.classify = v4_classify
verify_feed.EDITORIAL_SURFACES = set(verify_feed.EDITORIAL_SURFACES) | {"entertainment"}

# Technology, Gaming and U.S. already run their own event clustering in the
# specialist refinement stage. Running the generic verifier's broader event
# clustering again was collapsing distinct specialist stories. Preserve its
# clustering for every other category; the final V5 dedupe still runs afterward.
_base_same_event = verify_feed.same_event
_SPECIALIST_DEDUPE_CATEGORIES = {"technology", "gaming", "us"}

def v4_same_event(a, b):
    ca = verify_feed.category(a)
    cb = verify_feed.category(b)
    if ca == cb and ca in _SPECIALIST_DEDUPE_CATEGORIES:
        return False
    return _base_same_event(a, b)

verify_feed.same_event = v4_same_event

if __name__ == "__main__":
    augment_us_pool('News')
    verify_feed.main()

    # The generic verifier intentionally clusters within tabs. Follow it with a
    # conservative cross-tab pass that removes only obvious duplicate copies among
    # ordinary subject tabs, preserving the removed coverage as relatedArticles.
    import cross_tab_integrity_fast
    cross_tab_integrity_fast.run(
        'News',
        'cross-tab-integrity-report.json',
        '--apply' in sys.argv,
    )

    import finalize_entertainment_v4
    finalize_entertainment_v4.main()
