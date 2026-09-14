from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
index=(ROOT/'index.html').read_text(encoding='utf-8')
js=(ROOT/'assets/card-feedback.js').read_text(encoding='utf-8')
css=(ROOT/'styles/card-feedback.css').read_text(encoding='utf-8')
patch=(ROOT/'scripts/patch_v2_frontend.py').read_text(encoding='utf-8')

assert index.count('styles/card-feedback.css?v=')==1, 'feedback CSS not injected exactly once'
assert index.count('assets/card-feedback.js?v=')==1, 'feedback JS not injected exactly once'
assert index.count('styles/v5-visual.css?v=')==1, 'V5 visual hierarchy CSS not present exactly once'
assert 'data-card-feedback-style="true"' in index
assert 'data-card-feedback-script="true"' in index

for label in ('D','NR','NW'):
    assert repr(label) in js or f'"{label}"' in js, f'missing feedback reason {label}'

assert 'localStorage' in js, 'feedback pools are not persistent across refreshes'
assert 'MutationObserver' in js, 'dynamic cards are not monitored'
assert "underreported.cardFeedback.v1" in js, 'storage namespace missing'
assert 'sameRecord' in js and 'urlKey' in js and 'titleKey' in js, 'specific article suppression identity missing'
assert "card.remove()" in js, 'clicked card is not removed'
assert 'event.preventDefault()' in js and 'event.stopPropagation()' in js, 'feedback clicks may leak into card links'
assert '.card-feedback-controls' in css and 'z-index:40' in css, 'feedback controls may be hidden by card UI'
assert 'padding-right:112px' in css, 'title/bookmark collision guard missing'

# D must suppress only the specific clicked article record. There must be no event-cluster
# or sibling-card deletion behavior in the feedback layer.
for forbidden in ('same_event','eventCluster','querySelectorAll(\'.news-item\').forEach(other','closestDuplicate'):
    assert forbidden not in js, f'D feedback contains broad duplicate-removal behavior: {forbidden}'

assert "styles/card-feedback.css':'style'" in patch
assert "assets/card-feedback.js':'script'" in patch

# Existing V5 visual hierarchy remains loaded; feedback is an additive final layer.
visual=(ROOT/'styles/v5-visual.css').read_text(encoding='utf-8')
assert '--v5-border:' in visual and '.v3-source-icon' in visual, 'existing V5 hierarchy/icon styling missing'

print('CARD FEEDBACK UX TEST PASS')
