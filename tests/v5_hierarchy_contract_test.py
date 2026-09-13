from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'assets/v5-hierarchy.js').read_text(encoding='utf-8')
css=(ROOT/'styles/v5-hierarchy.css').read_text(encoding='utf-8')
app=(ROOT/'assets/app-v2.js').read_text(encoding='utf-8')
patch=(ROOT/'scripts/patch_v5_render_bindings.py').read_text(encoding='utf-8')
frontend=(ROOT/'scripts/patch_v2_frontend.py').read_text(encoding='utf-8')
loader=(ROOT/'assets/location-v2.js').read_text(encoding='utf-8')

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

# Underreported keeps its original age-band rail instead of being flattened into
# the purple semantic Analysis rail.
for band,color in {
    'blue':'#2563eb','green':'#16a34a','orange':'#f97316','purple':'#9333ea','red':'#dc2626'
}.items():
    assert f'data-age-band="{band}"' in css
    assert color in css
assert ':not(.underreported-item)' in css
assert 'data-age-band=\\"blue\\"' in frontend or 'data-age-band="blue"' in frontend
assert 'data-age-band=\\"red\\"' in frontend or 'data-age-band="red"' in frontend

# Visible badge/icon contract includes all hierarchy states.
assert ".v3-importance.high::before" in css
assert ".v3-importance.analysis::before" in css
assert ".v3-importance.local::before" in css
assert ".v3-importance.trending::before" in css
assert ".v3-importance.standard::before" in css

# Persistent critical CSS + final bootstrap are part of every canonical V5 page.
assert 'v5-hierarchy-critical-v1' in frontend
assert 'v5-hierarchy-bootstrap-v1' in frontend
assert 'styles/v5-hierarchy.css?v=4' in frontend
assert 'assets/v5-hierarchy.js?v=5' in frontend
assert 'assets/location-v2.js?v=8' in frontend
assert frontend.index('styles/v5-visual.css') < frontend.index('styles/v5-hierarchy.css') < frontend.index('v5-hierarchy-critical-v1')

# Fallback loader matches the same cache-busted hierarchy assets.
assert 'styles/v5-hierarchy.css?v=4' in loader
assert 'assets/v5-hierarchy.js?v=5' in loader

print('V5 hierarchy contract passed: persistent rails/icons enabled and Underreported age-band colors preserved.')
