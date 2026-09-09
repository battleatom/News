from pathlib import Path
import re
import subprocess
import sys

P = Path('index.html')
MARKER = '<script id="shared-page-state-bridge-v1">'
SCRIPT = r'''<script id="shared-page-state-bridge-v1">
(function(){
  'use strict';
  if(typeof window.allItems==='undefined' || typeof window.lastSuccessfulPull==='undefined' || typeof window.nextScheduledPull==='undefined' || typeof window.pullInProgress==='undefined'){
    throw new Error('Shared page state was not exposed as global variables.');
  }
})();
</script>'''

# patch_site_features.py runs immediately before this script in the main news
# workflow. Apply the resilient refresh handler here so refresh is part of the
# same build/deploy and no second automatic workflow can race the generated page.
subprocess.run([sys.executable, 'scripts/patch_refresh_success.py'], check=True)

s = P.read_text(encoding='utf-8')
if 'refresh-success-handling-v1' not in s:
    raise SystemExit('Integrated refresh success handling marker is missing')

# The page's canonical state used top-level let declarations. Those are lexical
# globals and therefore invisible to window-based feature modules. Convert only
# the shared state declarations to var so they are true window globals.
old_all = "let allItems=[],active=localStorage.getItem('underreported-active-tab')||'top';"
new_all = "var allItems=[],active=localStorage.getItem('underreported-active-tab')||'top';"
if old_all in s:
    s = s.replace(old_all, new_all, 1)
old_pull = "let lastSuccessfulPull=0,nextScheduledPull=0,pullInProgress=false;"
new_pull = "var lastSuccessfulPull=0,nextScheduledPull=0,pullInProgress=false;"
if old_pull in s:
    s = s.replace(old_pull, new_pull, 1)
if old_all not in s and new_all not in s:
    raise SystemExit('Could not locate allItems shared state declaration')
if old_pull not in s and new_pull not in s:
    raise SystemExit('Could not locate refresh shared state declaration')

while MARKER in s:
    a = s.find(MARKER)
    b = s.find('</script>', a)
    if b < 0:
        break
    s = s[:a] + s[b + 9:]
if '</body>' not in s:
    raise SystemExit('Missing </body> in index.html')
s = s.replace('</body>', SCRIPT + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Integrated resilient refresh handling, exposed shared page state as real window globals, and installed the validation bridge.')
