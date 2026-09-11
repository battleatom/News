from pathlib import Path
import re

# This patch runs after the other collector/dedupe patchers so final category
# quality rules cannot be accidentally widened by an earlier compatibility patch.

collector = Path("scripts/update_news.py")
source = collector.read_text(encoding="utf-8")

FOUR_CORNERS_QUERIES = [
    "Farmington New Mexico news",
    "San Juan County New Mexico news",
    "Aztec New Mexico news",
    "Bloomfield New Mexico news",
    "Kirtland New Mexico news",
    "Shiprock New Mexico news",
    "Four Corners news",
    "Durango Colorado news",
    "La Plata County Colorado news",
    "Cortez Colorado news",
    "Montezuma County Colorado news",
    "Gallup New Mexico news",
    "Window Rock Arizona news",
    "Navajo Nation news",
    "Blanding Utah news",
    "San Juan County Utah news",
    "Farmington NM crime government education business",
]

query_block = '    "local": [\n' + ''.join(f'        "{q}",\n' for q in FOUR_CORNERS_QUERIES) + '    ],\n'
source, n1 = re.subn(
    r'    "local": \[\n.*?    \],\n    "region": \{',
    query_block + '    "region": {',
    source,
    count=1,
    flags=re.S,
)
if n1 != 1:
    raise SystemExit("Could not canonicalize QUERIES['local']")

local_queries_block = 'LOCAL_QUERIES = [\n' + ''.join(f'    "{q}",\n' for q in FOUR_CORNERS_QUERIES) + ']\n'
source, n2 = re.subn(
    r'LOCAL_QUERIES = \[\n.*?\]\n\nMAINSTREAM_TOP_QUERIES',
    local_queries_block + '\nMAINSTREAM_TOP_QUERIES',
    source,
    count=1,
    flags=re.S,
)
if n2 != 1:
    raise SystemExit("Could not canonicalize LOCAL_QUERIES")

strict_local = '''    if items and items[0].get("category") == "local":
        local_terms = (
            "farmington", "san juan county", "aztec", "bloomfield", "kirtland",
            "shiprock", "navajo nation", "four corners", "san juan basin",
            "durango", "la plata county", "bayfield", "ignacio",
            "cortez", "montezuma county", "mancos", "dolores",
            "gallup", "mckinley county", "window rock", "chinle", "kayenta",
            "blanding", "monticello", "san juan county utah",
        )
        reject_terms = (
            "kirtland afb", "kirtland air force base",
        )
        local_items = []
        for item in items:
            title = (item.get("title") or "").lower()
            desc = (item.get("description") or "").lower()
            searchable = f"{title} {desc}"
            if any(term in searchable for term in reject_terms):
                continue
            if any(term in searchable for term in local_terms):
                local_items.append(item)
        items = local_items
'''
source, n3 = re.subn(
    r'    if items and items\[0\]\.get\("category"\) == "local":\n.*?        items = local_items\n',
    strict_local,
    source,
    count=1,
    flags=re.S,
)
if n3 != 1:
    raise SystemExit("Could not install strict Four Corners story relevance")

collector.write_text(source, encoding="utf-8")

# Federal dedupe lives in the legacy engine when the event-cluster wrapper is present.
dedupe_candidates = (
    Path("scripts/dedupe_news_legacy.py"),
    Path("scripts/dedupe_news_stories.py"),
)
old = '''    if ca == "federal" and same_federal_state_event(a, b):
        return True

    if smaller >= 5 and common / smaller >= 0.90:
'''
new = '''    if ca == "federal":
        if same_federal_state_event(a, b):
            return True
        fa, fb = content_tokens(a), content_tokens(b)
        federal_common = len(fa & fb)
        federal_smaller = min(len(fa), len(fb))
        # Keep clearly identical federal events, but preserve distinct court
        # cases, agency actions and congressional stories.
        if federal_common >= 5 and federal_smaller >= 6 and federal_common / federal_smaller >= 0.78:
            return True
        return very_close_title(a, b, minimum_common=5, ratio=0.92)

    if smaller >= 5 and common / smaller >= 0.90:
'''

verified = False
for dedupe in dedupe_candidates:
    if not dedupe.exists():
        continue
    dtext = dedupe.read_text(encoding="utf-8")
    if 'if ca == "federal":\n        if same_federal_state_event' in dtext:
        verified = True
        continue
    if old in dtext:
        dedupe.write_text(dtext.replace(old, new, 1), encoding="utf-8")
        verified = True

if not verified:
    raise SystemExit("Could not install Federal-specific dedupe threshold")

print("Enforced strict Four Corners story relevance and Federal-specific event dedupe.")
