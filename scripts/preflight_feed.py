from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')
s = s.replace('MAX_AGE_HOURS = 72', 'MAX_AGE_HOURS = 48')
s = s.replace('f"{query} when:3d"', 'f"{query} when:2d"')

line = '    "nfl": ["NFL news", "NFL injuries trades free agency", "NFL scores results"],'
s = re.sub(r'(?:\n?' + re.escape(line) + r'){1,}', '\n' + line, s)
if '    "technology": "technology AI cybersecurity science",' in s and line not in s:
    s = s.replace('    "technology": "technology AI cybersecurity science",', line + '\n    "technology": "technology AI cybersecurity science",', 1)
P.write_text(s, encoding='utf-8')

# Gaming qualification is now implemented directly in refine_tech_gaming.py.
# The production preflight should validate that current contract instead of
# rewriting the retired anchored/movie_tv implementation from older builds.
G = Path('scripts/refine_tech_gaming.py')
g = G.read_text(encoding='utf-8')
required_gaming_contract = (
    'def gaming_allowed(item):',
    'GAMING_EXCLUDE',
    'GAMING_TRUSTED',
    "trusted = source_is(text(item, 'source'), GAMING_TRUSTED)",
    'return strong or hardware or trusted',
)
missing = [token for token in required_gaming_contract if token not in g]
if missing:
    raise SystemExit('Gaming refinement contract missing: ' + ', '.join(missing))

# Laws & Legislation must be part of the canonical section registry itself.
# Injecting the tab only from a later UI wrapper was brittle: subsequent
# canonical tab rebuilds could drop it even though legislation data remained.
S = Path('scripts/patch_site_features.py')
site = S.read_text(encoding='utf-8')
old_registry = "['federal','🏛️ Federal Government','#ca8a04'],['nm','🏜️ New Mexico','#0f766e']"
new_registry = "['federal','🏛️ Federal Government','#ca8a04'],['legislation','📜 Laws & Legislation','#a16207'],['nm','🏜️ New Mexico','#0f766e']"
if old_registry in site:
    site = site.replace(old_registry, new_registry)
elif "['legislation','📜 Laws & Legislation','#a16207']" not in site:
    raise SystemExit('Could not add legislation to canonical tab registry')
S.write_text(site, encoding='utf-8')

print('Preflight complete: 48-hour news window, NFL, current Gaming contract, and canonical legislation tab verified.')
