#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
patch = (ROOT/'scripts/patch_v5_render_bindings.py').read_text(encoding='utf-8')
build = (ROOT/'scripts/build_site.py').read_text(encoding='utf-8')
css = (ROOT/'styles/v5-hierarchy.css').read_text(encoding='utf-8')
frontend = (ROOT/'scripts/patch_v2_frontend.py').read_text(encoding='utf-8')

# Hierarchy is attached when the canonical card is created, not inferred later.
assert "ar.dataset.hierarchy=kind" in patch
assert "ar.dataset.v5Hierarchy=kind" in patch
assert "ar.dataset.section=active" in patch
assert "ar.dataset.rank=String(i+1)" in patch
assert "ar.dataset.storyUrl=link" in patch
assert "ar.dataset.publishedAt=date" in patch
assert "data-v5-hierarchy-badge" in patch

# Every canonical render explicitly tells time-sensitive NEW UI that cards changed.
assert "underreported:feed-rendered" in patch
assert "window.decorateNewBadges" in patch

# The persistent CSS binds directly to semantic card data and loads after normal V5 CSS.
for kind in ('high','analysis','local','trending','standard'):
    assert f'data-hierarchy=\\"{kind}\\"' in css or f'data-hierarchy="{kind}"' in css
assert frontend.index('styles/v5-visual.css') < frontend.index('styles/v5-hierarchy.css')
assert 'styles/v5-hierarchy.css?v=3' in frontend
assert 'assets/v5-hierarchy.js?v=4' in frontend

# Canonical build must always apply the binding patch near the end of the pipeline.
assert "'scripts/patch_v5_render_bindings.py'" in build
assert build.index("'scripts/patch_entertainment_v4_ui.py'") < build.index("'scripts/patch_v5_render_bindings.py'") < build.index("'scripts/finalize_v5_html.py'")

print('V5 render-bound hierarchy contract passed.')
