from pathlib import Path
import re

P=Path('index.html')
s=P.read_text(encoding='utf-8')
s=re.sub(r'\s*<script[^>]+src="assets/location-content-v25\.js[^>]*></script>','',s)
# V2.8.1 includes stronger same-event dedupe in the externally loaded location
# controller. Bump the query version so browsers do not reuse the V2.7/V2.8 asset.
script='\n<script src="assets/location-content-v25.js?v=3"></script>\n'
if '</body>' not in s: raise SystemExit('Missing </body>')
s=s.replace('</body>',script+'</body>',1)
P.write_text(s,encoding='utf-8')
print('Applied V2.8.1 location-aware State/Regional/Local controller with event dedupe.')
