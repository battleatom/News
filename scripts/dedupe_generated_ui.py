from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Generated feature patches are identified by an explicit id. A duplicate
# script can register handlers twice and a duplicate style can hide later CSS,
# so canonicalize every generated script/style block rather than maintaining a
# hand-written allowlist of duplicate-prone features.
block_re = re.compile(
    r'<(?P<tag>script|style)\b(?P<attrs>[^>]*\bid=["\'](?P<id>[^"\']+)["\'][^>]*)>.*?</(?P=tag)>\s*',
    re.I | re.S,
)

# Retired UI belongs here so old generated pages are cleaned during the normal
# canonicalization pass instead of needing another feature patch.
RETIRED_BLOCK_IDS = {'story-search-v1', 'story-search-v1-style'}

matches = list(block_re.finditer(s))
by_key = {}
remove = []
for m in matches:
    key = (m.group('tag').lower(), m.group('id'))
    if m.group('id') in RETIRED_BLOCK_IDS:
        remove.append(m)
        continue
    by_key.setdefault(key, []).append(m)

for (tag, block_id), group in by_key.items():
    if len(group) <= 1:
        continue
    remove.extend(group[:-1])
    print(f'Removed {len(group)-1} duplicate {tag}#{block_id} block(s).')

retired_count = sum(1 for m in remove if m.group('id') in RETIRED_BLOCK_IDS)
if retired_count:
    print(f'Removed {retired_count} retired story-search block(s).')

for m in sorted(remove, key=lambda x: x.start(), reverse=True):
    s = s[:m.start()] + s[m.end():]

s, input_count = re.subn(r'<input\b[^>]*\bid=["\']story-search["\'][^>]*>\s*', '', s, flags=re.I | re.S)
if input_count:
    print(f'Removed {input_count} retired story-search input(s).')

# Hard verification: if an id-bearing generated script/style is still repeated,
# fail now rather than deploying a page with double event handlers.
remaining = list(block_re.finditer(s))
seen = set()
duplicates = []
for m in remaining:
    key = (m.group('tag').lower(), m.group('id'))
    if key in seen:
        duplicates.append(f'{key[0]}#{key[1]}')
    seen.add(key)
if duplicates:
    raise SystemExit('Duplicate generated UI blocks remain: ' + ', '.join(sorted(set(duplicates))))

if 'story-search' in s:
    raise SystemExit('Retired story search UI is still present after generated UI cleanup')

P.write_text(s, encoding='utf-8')
print(f'Generated UI cleanup complete: {len(seen)} unique id-bearing script/style blocks verified.')
