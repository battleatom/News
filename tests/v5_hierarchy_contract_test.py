from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'assets/v5-hierarchy.js').read_text(encoding='utf-8')
css=(ROOT/'styles/v5-hierarchy.css').read_text(encoding='utf-8')
loader=(ROOT/'assets/location-v2.js').read_text(encoding='utf-8')
app=(ROOT/'assets/app-v2.js').read_text(encoding='utf-8')

# V4 behavior stays intact: oversized lead styling remains removed.
assert "classList.remove('lead-story-v2')" in app

# V5 hierarchy must no longer depend on the removed V4 lead class.
assert "lead-story-v2" not in js
assert "v5-hierarchy-high" in js
assert "v5-hierarchy-analysis" in js
assert "v5-hierarchy-local" in js
assert "v5-hierarchy-trending" in js
assert "v5-hierarchy-standard" in js
assert "new Set(['nm','local','region'])" in js

# Rails use direct semantic classes; no :has dependency is required for the fix.
for name in ('high','analysis','local','trending','standard'):
    assert f'.news-item.v5-hierarchy-{name}' in css

# Visible badge/icon contract includes Standard too.
assert ".v3-importance.standard::before" in css

# Loader must cache-bust and load both bridge assets exactly once.
assert "assets/v3-ui.js?v=4" in loader
assert "styles/v5-hierarchy.css?v=1" in loader
assert "assets/v5-hierarchy.js?v=1" in loader

print('V5 hierarchy contract passed: V4 behavior preserved, semantic rails and icon badges enabled.')
