#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import update_news_location_validated as loc

farmington = next(m for m in loc.NEWS_MARKETS if m['id'] == 'farmington-nm')

# Local: direct city mention is accepted.
assert loc.strict_local_story_relevant({
    'title':'Farmington council approves downtown project',
    'description':'City leaders voted Tuesday.',
    'source':'Reuters',
}, farmington)

# Local: same-state-only generic story must not be accepted as Farmington-local.
assert not loc.strict_local_story_relevant({
    'title':'New Mexico State vs Hawaii prediction and odds',
    'description':'College football preview in New Mexico.',
    'source':'Yahoo Sports',
}, farmington)

# Local: an approved local newsroom may carry a nearby story without repeating city name.
assert loc.strict_local_story_relevant({
    'title':'County commissioners approve water project',
    'description':'The board approved the project this week.',
    'source':'Tri-City Record',
}, farmington)

# Local: approved local source is rejected when the article clearly belongs to another state.
assert not loc.strict_local_story_relevant({
    'title':'Texas lawmakers approve statewide measure',
    'description':'Texas officials announced the vote.',
    'source':'Tri-City Record',
}, farmington)

# Region: query-state must be supported by the actual story.
assert loc.strict_region_story_relevant({
    'title':'Texas drought emergency expands across western counties',
    'description':'Texas officials issued new restrictions.',
    'source':'Reuters',
}, 'Texas')

assert not loc.strict_region_story_relevant({
    'title':'Minnesota Vikings enter the 2026 season',
    'description':'The NFL club released its roster.',
    'source':'Yahoo Sports',
}, 'Texas')

assert not loc.strict_region_story_relevant({
    'title':'Massachusetts high school football scores',
    'description':'Friday night results from across Massachusetts.',
    'source':'Yahoo Sports',
}, 'Texas')

# The browser-side region controller must remain location-relative.
controller = (ROOT / 'assets' / 'location-content-v25.js').read_text(encoding='utf-8')
assert "region:STATE_REGION[code]||''" in controller
assert "matchesRegion(item,loc)" in controller
assert "itemRegion(item)===loc.region" in controller
assert "['region','local'].includes(category(i))&&matchesRegion(i,loc)" in controller

print('LOCATION VALIDATION TEST PASSED')
