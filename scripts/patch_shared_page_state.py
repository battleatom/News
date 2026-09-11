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
refresh_v3 = 'refresh-success-handling-v3' in s
refresh_v2 = 'refresh-success-handling-v2' in s
if not (refresh_v3 or refresh_v2):
    raise SystemExit('Explicit render-aware refresh success handling step must run before shared page state')

if 'const sections=[' in s:
    s = s.replace('const sections=[', 'var sections=[', 1)
elif 'var sections=[' not in s:
    raise SystemExit('Could not locate canonical sections declaration')

site_script = re.compile(r'(<script id="site-features-v2">.*?)(?:\r?\n)?loadNews\(false\);(\s*</script>)', re.S)
s, removed_eager_load = site_script.subn(r'\1\2', s, count=1)
if removed_eager_load != 1:
    raise SystemExit('Could not remove eager site-features loadNews(false) startup call')

# V3 already renders existing allItems inside its transient-failure catch. Older
# generated pages need the fallback injected here for backward compatibility.
if not refresh_v3:
    fallback_anchor = "if(allItems.length){\n      if(status)status.textContent='Refresh unavailable · showing '+allItems.length+' current stories';"
    fallback_replacement = "if(allItems.length){\n      try{canonicalBuildTabs();canonicalRender(allItems);decorateNewBadges();}catch(renderExistingError){console.error('Unable to render existing feed after refresh failure:',renderExistingError);}\n      if(status)status.textContent='Refresh unavailable · showing '+allItems.length+' current stories';"
    if fallback_anchor in s:
        s = s.replace(fallback_anchor, fallback_replacement, 1)
    else:
        raise SystemExit('Could not add existing-feed render fallback to refresh handler')

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
print('Integrated resilient refresh state, removed the duplicate startup fetch, exposed shared globals, and installed the validation bridge.')
