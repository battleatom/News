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
ASSET.write_text(asset,encoding='utf-8')

s=P.read_text(encoding='utf-8')
s=re.sub(r'\s*<script[^>]+src="assets/location-content-v25\.js[^>]*></script>','',s)
script='\n<script src="assets/location-content-v25.js?v=2"></script>\n'
if '</body>' not in s: raise SystemExit('Missing </body>')
s=s.replace('</body>',script+'</body>',1)
P.write_text(s,encoding='utf-8')
print('Applied V4 nationwide location hub and canonical state-region mapping.')
