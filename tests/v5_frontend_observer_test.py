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
assert "if(badge.textContent!==expectedLabel)" in hierarchy

# Hierarchy cards are rendered inside nested section containers. Watch the feed subtree,
# but filter mutations to story insertions so our own badge insertion cannot loop.
assert "observe(feed,{childList:true,subtree:true});" in hierarchy
assert "feedChanged(mutations)" in hierarchy
assert "containsStoryNode(node)" in hierarchy
assert "node.matches?.('.news-item')" in hierarchy

# The legacy V3 observer remains top-level only; hierarchy owns nested card decoration.
assert "observe(feed,{childList:true});" in v3
assert "observe(feed,{childList:true,subtree:true})" not in v3

# Cache-bust the repaired hierarchy assets for mobile browsers.
assert 'styles/v5-hierarchy.css?v=2' in patch
assert 'assets/v5-hierarchy.js?v=3' in patch
assert 'assets/location-v2.js?v=6' in patch

print('V5 frontend observer/runtime test passed.')
