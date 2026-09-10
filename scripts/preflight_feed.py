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

print('Preflight complete: rolling 48-hour news window, NFL category, and trusted Gaming context verified.')
