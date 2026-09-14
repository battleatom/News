#!/usr/bin/env python3
"""Final NFL feed guard.

Runs after editorial routing so ambiguous team aliases cannot pull unrelated stories
into the NFL tab. In particular, the standalone word "commanders" is not sufficient
NFL evidence unless the story also contains Washington/NFL/football context.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from clean_news import NFL_BLOCK_TERMS, NFL_RELEVANCE_TERMS, clean

NEWS = Path('News')

AMBIGUOUS_ALIASES = {'commanders'}
COMMANDERS_CONTEXT = (
    'washington commanders', 'nfl', 'football', 'quarterback', 'touchdown',
    'wide receiver', 'running back', 'tight end', 'head coach', 'coach',
    'roster', 'draft', 'playoff', 'kickoff', 'season opener', 'regular season',
)


def normalized(value: str) -> str:
    return re.sub(r'\s+', ' ', clean(value or '')).strip().lower()


def nfl_relevant(item: ET.Element) -> bool:
    title = normalized(item.findtext('title'))
    desc = normalized(item.findtext('description'))
    text = f'{title} {desc}'

    if any(term in text for term in NFL_BLOCK_TERMS):
        return False

    # All established NFL evidence remains valid except ambiguous standalone aliases.
    safe_terms = tuple(term for term in NFL_RELEVANCE_TERMS if term not in AMBIGUOUS_ALIASES)
    if any(term in title for term in safe_terms):
        return True

    if re.search(r'\bcommanders\b', title):
        return any(term in text for term in COMMANDERS_CONTEXT)

    return False


def main() -> None:
    tree = ET.parse(NEWS)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')

    removed = []
    for item in list(channel.findall('item')):
        category = normalized(item.findtext('category'))
        if category != 'nfl':
            continue
        if nfl_relevant(item):
            continue
        removed.append(normalized(item.findtext('title')))
        channel.remove(item)

    tree.write(NEWS, encoding='utf-8', xml_declaration=True)
    print(f'Final NFL relevance guard removed {len(removed)} non-NFL item(s).')
    for title in removed[:20]:
        print('  removed:', title)


if __name__ == '__main__':
    main()
