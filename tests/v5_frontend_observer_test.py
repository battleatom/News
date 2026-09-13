#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
hierarchy=(ROOT/'assets/v5-hierarchy.js').read_text(encoding='utf-8')
v3=(ROOT/'assets/v3-ui.js').read_text(encoding='utf-8')
patch=(ROOT/'scripts/patch_v2_frontend.py').read_text(encoding='utf-8')

# The hierarchy bridge must be explicit and independent of the removed V4 lead-card class.
assert 'v5-hierarchy-high' in hierarchy
assert "card.classList.contains('lead-story-v2')" not in hierarchy
assert "dataset.v5Hierarchy" in hierarchy
assert "dataset.hierarchy" in hierarchy
assert "if(badge.textContent!==expectedLabel)" in hierarchy

# Canonical cards are render-bound. The bridge still watches nested special renderers,
# but filters mutations to story insertions so its own badge insertion cannot loop.
assert "observe(feed,{childList:true,subtree:true});" in hierarchy
assert "feedChanged(mutations)" in hierarchy
assert "containsStoryNode(node)" in hierarchy
assert "node.matches?.('.news-item')" in hierarchy
assert "underreported:feed-rendered" in hierarchy

# The legacy V3 observer remains top-level only.
assert "observe(feed,{childList:true});" in v3
assert "observe(feed,{childList:true,subtree:true})" not in v3

# Cache-bust the persistent hierarchy assets for mobile browsers, while the inline
# critical CSS/bootstrap provide a no-network fallback inside the generated page.
assert 'styles/v5-hierarchy.css?v=4' in patch
assert 'assets/v5-hierarchy.js?v=5' in patch
assert 'assets/location-v2.js?v=8' in patch
assert 'v5-hierarchy-critical-v1' in patch
assert 'v5-hierarchy-bootstrap-v1' in patch
assert ':not(.underreported-item)' in patch

print('V5 frontend observer/runtime test passed.')
