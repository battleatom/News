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
# knows how to call registered category renderers.
legacy_boxoffice_wrapper = """  render=locationAwareRender;
  if(previousCanonicalRender){
    canonicalRender=function(items){
      if(active==='boxoffice') return locationAwareRender(items);
      return previousCanonicalRender(items);
    };
  }"""
registry_boxoffice = """  window.__categoryRenderers=window.__categoryRenderers||{};
  window.__categoryRenderers.boxoffice=locationAwareRender;"""

legacy_count = s.count(legacy_boxoffice_wrapper)
if legacy_count > 1:
    raise SystemExit(f'V5 finalizer found {legacy_count} Box Office canonical wrappers')
if legacy_count == 1:
    s = s.replace(legacy_boxoffice_wrapper, registry_boxoffice, 1)
elif registry_boxoffice not in s:
    raise SystemExit('V5 finalizer could not locate the Box Office renderer registration point')

# The pagination router previously bypassed its renderer registry for Box Office
# because the Box Office module owned a wrapper. Once Box Office is registered,
# only bookmarks need the bypass.
boxoffice_bypass = "if(active==='bookmarks'||active==='boxoffice'){"
bypass_count = s.count(boxoffice_bypass)
if bypass_count > 1:
    raise SystemExit(f'V5 finalizer found {bypass_count} Box Office pagination bypasses')
if bypass_count == 1:
    s = s.replace(boxoffice_bypass, "if(active==='bookmarks'){", 1)

# Hard gate the architecture here so a future patch cannot silently recreate
# the duplicate wrapper that blocked this release.
wrapper_count = len(re.findall(r'canonicalRender\s*=\s*function\s*\(items\)', s))
if wrapper_count != 1:
    raise SystemExit(f'V5 finalizer expected one canonical pagination wrapper, found {wrapper_count}')
if registry_boxoffice not in s:
    raise SystemExit('V5 finalizer lost the Box Office category renderer registration')
if boxoffice_bypass in s:
    raise SystemExit('V5 finalizer left the retired Box Office pagination bypass in place')

P.write_text(s, encoding='utf-8')
print(
    f'Finalized V5 HTML: collapsed {len(matches)} sections declaration(s), '
    'registered Box Office through the category router, and verified one canonical pagination wrapper.'
)
