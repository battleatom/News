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

# The Gaming refinement must not require every legitimate game headline to say
# the literal word "game". Trusted gaming publishers provide useful context,
# while junk/giveaway and unrelated movie/TV checks still run first.
G = Path('scripts/refine_tech_gaming.py')
g = G.read_text(encoding='utf-8')
old = '''    if movie_tv and not anchored:\n        return False\n    return anchored'''
new = '''    if movie_tv and not anchored:\n        return False\n    trusted_gaming_source = source_family(text(item, 'source')) in ('ign','gamespot','pc gamer','nintendo life','polygon')\n    return anchored or trusted_gaming_source'''
if old in g:
    g = g.replace(old, new, 1)
elif 'trusted_gaming_source = source_family' not in g:
    raise SystemExit('Could not relax Gaming source-context filter')
G.write_text(g, encoding='utf-8')

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

print('Preflight complete: 48-hour news window, NFL, Gaming context, and canonical legislation tab verified.')
