#!/usr/bin/env python3
"""Final V5 HTML normalization.

Keep the generated page deterministic by collapsing repeated standalone `sections`
declarations and by enforcing one canonical pagination wrapper. Box Office is a
category renderer, not a second canonicalRender owner.
"""
from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Collapse repeated standalone section declarations to one canonical declaration.
pattern = re.compile(
    r'(?m)^[ \t]*(?:const|var)\s+sections=\[[^\n]*\];[ \t]*(?:\n|$)'
)
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

# Box Office used to wrap canonicalRender directly. That created a second
# pagination owner and made the production audit fail. Register it through the
# existing category-renderer registry instead; the pagination router already
# knows how to call registered category renderers. Match by syntax, not exact
# whitespace, because later HTML normalizers may reformat assignment spacing.
legacy_boxoffice_pattern = re.compile(
    r"\s*render\s*=\s*locationAwareRender\s*;\s*"
    r"if\s*\(\s*previousCanonicalRender\s*\)\s*\{\s*"
    r"canonicalRender\s*=\s*function\s*\(\s*items\s*\)\s*\{\s*"
    r"if\s*\(\s*active\s*===\s*['\"]boxoffice['\"]\s*\)\s*return\s+locationAwareRender\s*\(\s*items\s*\)\s*;\s*"
    r"return\s+previousCanonicalRender\s*\(\s*items\s*\)\s*;\s*"
    r"\}\s*;\s*\}\s*;?",
    re.S,
)
registry_boxoffice_pattern = re.compile(
    r"window\.__categoryRenderers\s*=\s*window\.__categoryRenderers\s*\|\|\s*\{\s*\}\s*;\s*"
    r"window\.__categoryRenderers\.boxoffice\s*=\s*locationAwareRender\s*;",
    re.S,
)
registry_boxoffice = (
    "  window.__categoryRenderers=window.__categoryRenderers||{};\n"
    "  window.__categoryRenderers.boxoffice=locationAwareRender;"
)

legacy_matches = list(legacy_boxoffice_pattern.finditer(s))
if len(legacy_matches) > 1:
    raise SystemExit(f'V5 finalizer found {len(legacy_matches)} Box Office canonical wrappers')
if len(legacy_matches) == 1:
    s = legacy_boxoffice_pattern.sub('\n' + registry_boxoffice, s, count=1)
elif not registry_boxoffice_pattern.search(s):
    raise SystemExit('V5 finalizer could not locate the Box Office renderer registration point')

# The pagination router previously bypassed its renderer registry for Box Office
# because the Box Office module owned a wrapper. Once Box Office is registered,
# only bookmarks need the bypass. Accept whitespace variations from normalizers.
boxoffice_bypass_pattern = re.compile(
    r"if\s*\(\s*active\s*===\s*['\"]bookmarks['\"]\s*\|\|\s*active\s*===\s*['\"]boxoffice['\"]\s*\)\s*\{"
)
bypass_matches = list(boxoffice_bypass_pattern.finditer(s))
if len(bypass_matches) > 1:
    raise SystemExit(f'V5 finalizer found {len(bypass_matches)} Box Office pagination bypasses')
if len(bypass_matches) == 1:
    s = boxoffice_bypass_pattern.sub("if(active==='bookmarks'){", s, count=1)

# Hard gate the architecture here so a future patch cannot silently recreate
# the duplicate wrapper that blocked this release.
wrapper_count = len(re.findall(r'canonicalRender\s*=\s*function\s*\(\s*items\s*\)', s))
if wrapper_count != 1:
    raise SystemExit(f'V5 finalizer expected one canonical pagination wrapper, found {wrapper_count}')
if not registry_boxoffice_pattern.search(s):
    raise SystemExit('V5 finalizer lost the Box Office category renderer registration')
if boxoffice_bypass_pattern.search(s):
    raise SystemExit('V5 finalizer left the retired Box Office pagination bypass in place')

P.write_text(s, encoding='utf-8')
print(
    f'Finalized V5 HTML: collapsed {len(matches)} sections declaration(s), '
    'registered Box Office through the category router, and verified one canonical pagination wrapper.'
)
