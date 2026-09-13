from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent

def read(path):
    return (ROOT/path).read_text(encoding='utf-8')

patcher=read('scripts/patch_v2_frontend.py')
location=read('assets/location-v2.js')
presentation=read('assets/v3-ui.js')
visual=read('styles/v5-visual.css')
finalizer=read('scripts/finalize_v5_html.py')

# Location must own only location behavior; presentation is loaded explicitly once.
assert 'v3-ui.js' not in location, 'location-v2.js still loads presentation code'
assert "'assets/v3-ui.js':'script'" in patcher, 'frontend patcher does not explicitly own v3-ui.js'

# Cache busting must derive from file content rather than hand-maintained version numbers.
assert 'hashlib.sha256' in patcher and 'hexdigest()[:12]' in patcher, 'asset versioning is not content-hashed'
assert not re.search(r'v3-ui\.js\?v=\d+', patcher), 'manual v3-ui cache version remains'
assert not re.search(r'v5-visual\.css\?v=\d+', patcher), 'manual visual CSS cache version remains'

# Runtime JS must not inject visual CSS or retired hierarchy cleanup.
for token in ('document.createElement(\'style\')','v3-card-key','v3-importance','v5-hierarchy'):
    assert token not in presentation, f'presentation runtime still contains obsolete visual owner: {token}'

# Visual CSS is the single owner of Underreported age presentation.
for cls in ('.underreported-age-key','.age-blue','.age-green','.age-orange','.age-purple','.age-red'):
    assert cls in visual, f'visual stylesheet missing {cls}'
assert '.v3-card-key' not in visual, 'retired hierarchy fail-safe remains in canonical visual CSS'

# Final HTML guard must reject duplicate owners and retired hierarchy artifacts.
for asset in ('styles/v2.css','styles/v5-visual.css','assets/location-v2.js','assets/v3-ui.js','assets/app-v2.js'):
    assert asset in finalizer, f'finalizer does not guard {asset}'
for token in ('v5-hierarchy.js','v5-hierarchy.css','v3-card-key','v3-importance','lead-story-v2'):
    assert token in finalizer, f'finalizer does not reject retired token {token}'

print('V5 UX architecture ownership test passed.')
