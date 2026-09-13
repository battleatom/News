#!/usr/bin/env python3
"""V5 audit for external runtime ownership that the generated-HTML audit cannot see."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'index.html'
ASSETS=ROOT/'assets'
html=INDEX.read_text(encoding='utf-8')

required=('assets/app-v2.js','assets/location-content-v25.js','assets/location-city-only.js','assets/entertainment-v4.js')
for src in required:
    n=html.count(src)
    if n!=1:
        raise SystemExit(f'{src}: expected exactly one runtime reference, found {n}')

js={p.name:p.read_text(encoding='utf-8') for p in ASSETS.glob('*.js')}
wrap_owners=[name for name,text in js.items() if 'canonicalRender=wrapRenderer(canonicalRender)' in text]
if wrap_owners!=['app-v2.js']:
    raise SystemExit(f'canonical renderer wrapper ownership is ambiguous: {wrap_owners}')

# Category-specific surfaces should register with the renderer registry instead of
# replacing the canonical router themselves.
for name in ('entertainment-v4.js',):
    text=js.get(name,'')
    if '__categoryRenderers' not in text:
        raise SystemExit(f'{name}: category renderer registry registration missing')
    if re.search(r'canonicalRender\s*=\s*function',text):
        raise SystemExit(f'{name}: must not replace canonicalRender')

build=(ROOT/'scripts/build_site.py').read_text(encoding='utf-8')
if build.find("'scripts/patch_entertainment_v4_ui.py'") < build.find("'scripts/patch_system_health.py'"):
    raise SystemExit('Entertainment final wiring must occur after the shared/system patch chain')

print('V5 runtime ownership audit passed: one canonical external wrapper owner and one reference per required runtime asset.')
