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

# Feed observers must watch only top-level render replacement, not every badge/text mutation.
assert "observe(feed,{childList:true});" in hierarchy
assert "observe(feed,{childList:true,subtree:true})" not in hierarchy
assert "observe(feed,{childList:true});" in v3
assert "observe(feed,{childList:true,subtree:true})" not in v3

# Cache-bust the optimized hierarchy asset so mobile browsers cannot retain the old loop-prone file.
assert 'assets/v5-hierarchy.js?v=2' in patch

print('V5 frontend observer/idempotence test passed.')
