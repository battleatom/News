from pathlib import Path
import re

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

s = P.read_text(encoding='utf-8')
if 'refresh-success-handling-v2' not in s:
    raise SystemExit('Explicit render-aware refresh success handling step must run before shared page state')

if 'const sections=[' in s:
    s = s.replace('const sections=[', 'var sections=[', 1)
elif 'var sections=[' not in s:
    raise SystemExit('Could not locate canonical sections declaration')

site_script = re.compile(r'(<script id="site-features-v2">.*?)(?:\r?\n)?loadNews\(false\);(\s*</script>)', re.S)
s, removed_eager_load = site_script.subn(r'\1\2', s, count=1)
if removed_eager_load != 1:
    raise SystemExit('Could not remove eager site-features loadNews(false) startup call')

fallback_anchor = "if(allItems.length){\n      if(status)status.textContent='Refresh unavailable · showing '+allItems.length+' current stories';"
fallback_replacement = "if(allItems.length){\n      try{canonicalBuildTabs();canonicalRender(allItems);decorateNewBadges();}catch(renderExistingError){console.error('Unable to render existing feed after refresh failure:',renderExistingError);}\n      if(status)status.textContent='Refresh unavailable · showing '+allItems.length+' current stories';"
if fallback_anchor in s:
    s = s.replace(fallback_anchor, fallback_replacement, 1)
else:
    raise SystemExit('Could not add existing-feed render fallback to refresh handler')

# Convert whichever active-tab declaration is present into one true window-global
# state object. V2.8.2 intentionally starts on Top and restores the saved tab only
# after all specialized renderers have initialized.
state_variants = (
    "let allItems=[],active=localStorage.getItem('underreported-active-tab')||'top';",
    "var allItems=[],active=localStorage.getItem('underreported-active-tab')||'top';",
    "let allItems=[],active='top';window.__pendingActiveTab=localStorage.getItem('underreported-active-tab')||'top';",
    "var allItems=[],active='top';window.__pendingActiveTab=localStorage.getItem('underreported-active-tab')||'top';",
)
state_replacement = "var allItems=[],active='top';window.__pendingActiveTab=localStorage.getItem('underreported-active-tab')||'top';"
found_state = False
for old in state_variants:
    if old in s:
        s = s.replace(old, state_replacement, 1)
        found_state = True
        break
if not found_state:
    raise SystemExit('Could not locate compatible allItems/active shared state declaration')

old_pull = "let lastSuccessfulPull=0,nextScheduledPull=0,pullInProgress=false;"
new_pull = "var lastSuccessfulPull=0,nextScheduledPull=0,pullInProgress=false;"
if old_pull in s:
    s = s.replace(old_pull, new_pull, 1)
if new_pull not in s:
    raise SystemExit('Could not expose refresh shared state declarations')

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
print('Integrated resilient refresh state, deferred saved-tab startup, removed duplicate startup fetch, and exposed shared globals.')
