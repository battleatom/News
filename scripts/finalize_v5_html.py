#!/usr/bin/env python3
"""Final V5 HTML normalization and frontend ownership guard."""
from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Older patch generations can leave repeated standalone sections declarations.
pattern = re.compile(r'(?m)^[ \t]*(?:const|var)\s+sections=\[[^\n]*\];[ \t]*(?:\n|$)')
matches = list(pattern.finditer(s))
if not matches:
    raise SystemExit('V5 finalizer could not locate the canonical sections declaration')

first_start = matches[0].start()
canonical = matches[0].group(0).strip()
canonical = re.sub(r'^(?:const|var)\s+sections=', 'var sections=', canonical, count=1)
cleaned = pattern.sub('', s)
s = cleaned[:first_start] + canonical + '\n' + cleaned[first_start:]

final_matches = list(pattern.finditer(s))
if len(final_matches) != 1:
    raise SystemExit(f'V5 finalizer expected one sections declaration, found {len(final_matches)}')

# The V5 frontend has one explicit owner for each runtime asset. Any duplicate or
# retired hierarchy artifact means an earlier patch has leaked into the output.
owned_assets = [
    'styles/v2.css',
    'styles/v5-visual.css',
    'assets/location-v2.js',
    'assets/v3-ui.js',
    'assets/app-v2.js',
]
for asset in owned_assets:
    count = len(re.findall(re.escape(asset) + r'(?:\?[^"\']*)?', s))
    if count != 1:
        raise SystemExit(f'V5 finalizer expected one reference to {asset}, found {count}')

retired = ['v5-hierarchy.js', 'v5-hierarchy.css', 'v3-card-key', 'v3-importance', 'lead-story-v2']
for token in retired:
    if token in s:
        raise SystemExit(f'V5 finalizer found retired hierarchy artifact: {token}')

P.write_text(s, encoding='utf-8')
print(f'Finalized V5 HTML: one sections declaration, one owner per frontend asset, no retired hierarchy artifacts.')
