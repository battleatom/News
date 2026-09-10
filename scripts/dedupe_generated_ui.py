from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Generated feature patches are identified by an explicit id.  A duplicate
# script can register handlers twice and a duplicate style can hide later CSS,
# so canonicalize every generated script/style block rather than maintaining a
# hand-written allowlist of two ids.
block_re = re.compile(
    r'<(?P<tag>script|style)\b(?P<attrs>[^>]*\bid=["\'](?P<id>[^"\']+)["\'][^>]*)>.*?</(?P=tag)>\s*',
    re.I | re.S,
)

matches = list(block_re.finditer(s))
by_key = {}
for m in matches:
    key = (m.group('tag').lower(), m.group('id'))
    by_key.setdefault(key, []).append(m)

# Keep the last generated block. Later patches are the authoritative wrappers
# in this build, while earlier copies are stale versions left by older patches.
remove = []
for (tag, block_id), group in by_key.items():
    if len(group) <= 1:
        continue
    remove.extend(group[:-1])
    print(f'Removed {len(group)-1} duplicate {tag}#{block_id} block(s).')

for m in sorted(remove, key=lambda x: x.start(), reverse=True):
    s = s[:m.start()] + s[m.end():]

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

P.write_text(s, encoding='utf-8')
print(f'Generated UI deduplication complete: {len(seen)} unique id-bearing script/style blocks verified.')
