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

# Keep the strict final V5 Gaming threshold, but recognize the headline forms
# used by legitimate video-game coverage. This prevents a healthy 20-story
# refined pool from collapsing merely because a headline says PS5, Switch 2,
# Game Pass, Steam Deck, Unreal Engine, etc. instead of the literal word "gaming".
V5 = Path('scripts/v5_tab_filters.py')
v5 = V5.read_text(encoding='utf-8')
old_gaming_rule = '"gaming":TabRule(D(video_game=13,gaming=11,playstation=12,xbox=12,nintendo=12,steam=9,game_studio=10,game_developer=10,game_development=9,console=8,pc_gaming=11,pc_gamer=10,esports=10,gameplay=8,dlc=7,game_release=9),D(casino=-20,gambling=-20,sportsbook=-20,lottery=-18,slot_machine=-18),9,11),'
new_gaming_rule = '"gaming":TabRule(D(video_game=13,gaming=11,playstation=12,ps5=11,xbox=12,nintendo=12,switch_2=12,nintendo_switch=11,steam=9,steam_deck=11,game_pass=10,game_studio=10,game_developer=10,game_development=9,game_publisher=9,epic_games=9,unreal_engine=9,console=8,pc_gaming=11,pc_gamer=10,gaming_handheld=9,esports=10,gameplay=8,dlc=7,game_release=9,release_date=7),D(casino=-20,gambling=-20,sportsbook=-20,lottery=-18,slot_machine=-18,tabletop=-25,board_game=-25,miniatures=-25,warhammer=-25,trading_card=-22,hobby_store=-20),9,11),'
if old_gaming_rule in v5:
    v5 = v5.replace(old_gaming_rule, new_gaming_rule, 1)
elif 'switch_2=12' not in v5 or 'tabletop=-25' not in v5:
    raise SystemExit('Could not expand V5 Gaming headline anchors')
V5.write_text(v5, encoding='utf-8')

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

print('Preflight complete: 48-hour news window, NFL, expanded strict Gaming anchors, and canonical legislation tab verified.')
