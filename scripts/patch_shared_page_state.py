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
if 'refresh-success-handling-v2' not in s:
    raise SystemExit('Integrated render-aware refresh success handling marker is missing')

# patch_site_features owns the canonical category list and intentionally assigns
# sections=CANONICAL_SECTIONS at runtime. The generated base page historically
# declared sections with const, which makes that legitimate assignment throw
# "Assignment to constant variable" and abort the rest of site-features setup.
# Make this one shared, intentionally mutable binding a true window global.
if 'const sections=[' in s:
    s = s.replace('const sections=[', 'var sections=[', 1)
elif 'var sections=[' not in s:
    raise SystemExit('Could not locate canonical sections declaration')

# patch_site_features historically starts an eager loadNews(false) while the
# document is still being parsed. The canonical DOMContentLoaded loader added by
# patch_refresh_success.py starts a second fetch later. On mobile those two
# requests can race: one fills allItems while the other failure leaves the page
# stuck on "Loading news...". Remove the eager startup call so there is exactly
# one initial feed load, after every renderer (including NFL and Load More) exists.
site_script = re.compile(r'(<script id="site-features-v2">.*?)(?:\r?\n)?loadNews\(false\);(\s*</script>)', re.S)
s, removed_eager_load = site_script.subn(r'\1\2', s, count=1)
if removed_eager_load != 1:
    raise SystemExit('Could not remove eager site-features loadNews(false) startup call')

# If a later refresh fails after another path already populated allItems, render
# those existing items rather than allowing a stale "Loading news..." placeholder
# to remain visible.
fallback_anchor = "if(allItems.length){\n      if(status)status.textContent='Refresh unavailable · showing '+allItems.length+' current stories';"
fallback_replacement = "if(allItems.length){\n      try{canonicalBuildTabs();canonicalRender(allItems);decorateNewBadges();}catch(renderExistingError){console.error('Unable to render existing feed after refresh failure:',renderExistingError);}\n      if(status)status.textContent='Refresh unavailable · showing '+allItems.length+' current stories';"
if fallback_anchor in s:
    s = s.replace(fallback_anchor, fallback_replacement, 1)
else:
    raise SystemExit('Could not add existing-feed render fallback to refresh handler')

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
print('Integrated resilient refresh handling, removed the duplicate startup fetch, exposed mutable shared page state as real window globals, and installed the validation bridge.')
