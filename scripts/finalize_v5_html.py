#!/usr/bin/env python3
"""Final V5 HTML normalization.

Older patch generations can leave repeated standalone `sections` declarations in
index.html. They are runtime-equivalent but make successive canonical builds grow
by one declaration. Collapse them to one declaration at the end of every build so
V5 output is reproducible and byte-stable.
"""
from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

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

P.write_text(s, encoding='utf-8')
print(f'Finalized V5 HTML: collapsed {len(matches)} sections declaration(s) to one canonical declaration.')
