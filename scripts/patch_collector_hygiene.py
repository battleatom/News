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

P.write_text(s, encoding='utf-8')
print('Collector hygiene complete: duplicate generated literals canonicalized.')
