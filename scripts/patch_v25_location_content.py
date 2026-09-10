from pathlib import Path
import re

P=Path('index.html')
s=P.read_text(encoding='utf-8')
s=re.sub(r'\s*<script[^>]+src="assets/location-content-v25\.js[^>]*></script>','',s)
script='\n<script src="assets/location-content-v25.js?v=2"></script>\n'
if '</body>' not in s: raise SystemExit('Missing </body>')
s=s.replace('</body>',script+'</body>',1)
P.write_text(s,encoding='utf-8')
print('Applied V2.6 location-aware merged State/Regional/Local content controller.')
