from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'assets/v5-hierarchy.js').read_text(encoding='utf-8')
css=(ROOT/'styles/v5-hierarchy.css').read_text(encoding='utf-8')
app=(ROOT/'assets/app-v2.js').read_text(encoding='utf-8')
patch=(ROOT/'scripts/patch_v5_render_bindings.py').read_text(encoding='utf-8')
frontend=(ROOT/'scripts/patch_v2_frontend.py').read_text(encoding='utf-8')

# V4 behavior stays intact: oversized lead styling remains removed.
assert "classList.remove('lead-story-v2')" in app

# V5 hierarchy no longer depends on the removed V4 lead class.
assert "lead-story-v2" not in js
assert "dataset.hierarchy" in js
assert "dataset.v5Hierarchy" in js
assert "new Set(['nm','local','region'])" in js

# Canonical cards receive their hierarchy state at creation time.
assert "ar.dataset.hierarchy=kind" in patch
assert "ar.dataset.v5Hierarchy=kind" in patch
assert "data-v5-hierarchy-badge" in patch
assert "underreported:feed-rendered" in patch

# Rails bind directly to persistent semantic data, with class fallback.
for name in ('high','analysis','local','trending','standard'):
    assert f'[data-hierarchy="{name}"]' in css
    assert f'.news-item.v5-hierarchy-{name}' in css

# Visible badge/icon contract includes all hierarchy states.
assert ".v3-importance.high::before" in css
assert ".v3-importance.analysis::before" in css
assert ".v3-importance.local::before" in css
assert ".v3-importance.trending::before" in css
assert ".v3-importance.standard::before" in css

# The hierarchy stylesheet is cache-busted and intentionally follows normal V5 card CSS.
assert 'styles/v5-hierarchy.css?v=3' in frontend
assert 'assets/v5-hierarchy.js?v=4' in frontend
assert frontend.index('styles/v5-visual.css') < frontend.index('styles/v5-hierarchy.css')

print('V5 hierarchy contract passed: render-bound semantics, persistent rails, and icon badges enabled.')
