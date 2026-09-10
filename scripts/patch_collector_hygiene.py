from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')

# Older idempotent patchers occasionally appended the same literal more than
# once. Python accepts duplicate dict keys, but they are misleading and make it
# difficult to audit the collector. Canonicalize the known generated sections.
weight_match = re.search(r'CATEGORY_WEIGHT\s*=\s*\{.*?\}\n', s, flags=re.S)
if weight_match:
    canonical = 'CATEGORY_WEIGHT = {"world": 18, "us": 22, "presidential": 24, "federal": 22, "legislation": 24, "military": 20, "nfl": 18, "technology": 12, "gaming": 16, "nm": 8, "local": 6}\n'
    s = s[:weight_match.start()] + canonical + s[weight_match.end():]

# Repeated source token has no functional benefit and obscures source audits.
s = re.sub(r'("route fifty",\s*){2,}', '"route fifty", ', s)

# Keep enough candidate stories behind every paginated high-priority tab. The
# UI displays 10 initially, so a pool must contain more than 10 records for Load
# More to be meaningful. These minimums match the category-health targets.
POOL_MINIMUMS = {
    "local": 20,
    "nfl": 20,
    "presidential": 20,
    "federal": 25,
    "technology": 25,
    "gaming": 25,
}
minimum_block = 'CATEGORY_POOL_MINIMUMS = ' + repr(POOL_MINIMUMS) + '\n'
if 'CATEGORY_POOL_MINIMUMS =' in s:
    s = re.sub(r'CATEGORY_POOL_MINIMUMS\s*=\s*\{.*?\}\n', minimum_block, s, count=1, flags=re.S)
else:
    anchor = 'CATEGORY_WEIGHT = '
    pos = s.find(anchor)
    if pos < 0:
        raise SystemExit('Could not locate category weights for pool minimums')
    line_end = s.find('\n', pos)
    s = s[:line_end + 1] + minimum_block + s[line_end + 1:]

# Presidential needs several independent searches rather than one broad query;
# this gives the selector enough current White House material to retain 20-25
# distinct stories after source filtering and dedupe.
presidential_queries = '''    "presidential": [
        "Trump president White House",
        "President Trump administration White House policy",
        "Trump executive order presidential action White House",
        "Trump cabinet administration president",
    ],
'''
s, changed = re.subn(
    r'    "presidential":\s*(?:"[^"]*"|\[.*?\]),\n    "federal":',
    presidential_queries + '    "federal":',
    s,
    count=1,
    flags=re.S,
)
if changed != 1:
    raise SystemExit("Could not canonicalize QUERIES['presidential']")

# Add trusted source fallbacks for the two federal-news categories. The site
# already has this mechanism for NFL/Local/Tech/Gaming; extending the same
# collector path avoids adding another special-purpose pipeline.
fallback_entries = '''    "presidential": [
        ("Reuters", "site:reuters.com Trump White House president administration"),
        ("Associated Press", "site:apnews.com Trump White House president administration"),
        ("Politico", "site:politico.com Trump White House president administration"),
        ("CNN", "site:cnn.com Trump White House president administration"),
        ("CBS News", "site:cbsnews.com Trump White House president administration"),
    ],
    "federal": [
        ("Reuters", "site:reuters.com Congress Supreme Court DOJ FBI federal agency government"),
        ("Associated Press", "site:apnews.com Congress Supreme Court DOJ FBI federal government"),
        ("Politico", "site:politico.com Congress Supreme Court federal agency government"),
        ("The Hill", "site:thehill.com Congress Supreme Court federal agency government"),
        ("NPR", "site:npr.org Congress Supreme Court federal government agency"),
    ],
'''
# Remove earlier copies if this hygiene patch has already run, then insert one
# canonical pair at the start of the existing fallback dictionary.
for key in ('presidential', 'federal'):
    s = re.sub(
        rf'    "{key}": \[\n(?:        .*\n)*?    \],\n',
        '',
        s,
        count=1,
    ) if 'TRUSTED_CATEGORY_FALLBACKS = {' in s and s.find(f'    "{key}": [', s.find('TRUSTED_CATEGORY_FALLBACKS = {')) >= 0 else s
fallback_anchor = 'TRUSTED_CATEGORY_FALLBACKS = {\n'
if fallback_anchor not in s:
    raise SystemExit('Could not locate trusted category fallbacks')
s = s.replace(fallback_anchor, fallback_anchor + fallback_entries, 1)

# Trigger the trusted fallback path at the category's actual minimum instead of
# waiting until it falls below 10. This is the key reason NFL/Federal could show
# no Load More button even though their intended retained pools are much larger.
s = s.replace(
    'if category in TRUSTED_CATEGORY_FALLBACKS and usable_count < 10:',
    'if category in TRUSTED_CATEGORY_FALLBACKS and usable_count < CATEGORY_POOL_MINIMUMS.get(category, 10):',
)
s = s.replace(
    'target = 15 if category == "local" else 20',
    'target = CATEGORY_POOL_MINIMUMS.get(category, 20)',
)

# Gaming/Technology intentionally continue through all fallback publishers even
# after reaching their minimum so one outlet does not dominate the final pool.
old = '''                            target = CATEGORY_POOL_MINIMUMS.get(category, 20)\n                            if usable_count >= target:\n                                break'''
new = '''                            target = CATEGORY_POOL_MINIMUMS.get(category, 20)\n                            if usable_count >= target and category not in ("gaming", "technology"):\n                                break'''
if old in s:
    s = s.replace(old, new, 1)
elif 'category not in ("gaming", "technology")' not in s:
    raise SystemExit('Could not install diversified Gaming/Technology fallback collection')

P.write_text(s, encoding='utf-8')
print('Collector hygiene complete: category pools use target-aware trusted fallbacks.')
