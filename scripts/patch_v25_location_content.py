from pathlib import Path
import re

P=Path('index.html')
ASSET=Path('assets/location-content-v25.js')

# Keep the checked-in nationwide region table canonical before wiring the controller.
asset=ASSET.read_text(encoding='utf-8')
asset=asset.replace("SC:'northeast'", "SC:'southeast'")
if "SC:'southeast'" not in asset:
    raise SystemExit('South Carolina region mapping is missing or malformed')
if asset.count("MA:'Massachusetts'") != 1:
    raise SystemExit('State table must contain Massachusetts exactly once')

# Statewide pools must be allowed to draw from state-tagged local/region stories.
# Limiting non-NM states to only US/Top categories made valid Colorado stories
# invisible to the Colorado Statewide scope even while the Mountain pool was full.
old_state_candidates = "const candidates=items.filter(item=>{const cat=category(item);if(cat==='nm'&&loc.code==='NM')return true;return ['us','top'].includes(cat)&&matchesState(item,loc)});"
new_state_candidates = "const candidates=items.filter(item=>{const cat=category(item);if(cat==='nm'&&loc.code==='NM')return true;return ['us','top','region','local'].includes(cat)&&matchesState(item,loc)});"
if old_state_candidates in asset:
    asset=asset.replace(old_state_candidates,new_state_candidates,1)
elif new_state_candidates not in asset:
    raise SystemExit('State pool candidate rule is missing or malformed')

ASSET.write_text(asset,encoding='utf-8')

s=P.read_text(encoding='utf-8')
s=re.sub(r'\s*<script[^>]+src="assets/location-content-v25\.js[^>]*></script>','',s)
s=re.sub(r'\s*<script[^>]+src="assets/location-city-only\.js[^>]*></script>','',s)
script='\n<script src="assets/location-content-v25.js?v=3"></script>\n<script src="assets/location-city-only.js?v=2"></script>\n'
if '</body>' not in s: raise SystemExit('Missing </body>')
s=s.replace('</body>',script+'</body>',1)
P.write_text(s,encoding='utf-8')
print('Applied V5 nationwide location hub with combined State & County scope, city-only Local scope, and canonical state-region mapping.')