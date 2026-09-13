from pathlib import Path

html = Path('index.html').read_text(encoding='utf-8')
app = Path('assets/app-v2.js').read_text(encoding='utf-8')
css = Path('styles/v2.css').read_text(encoding='utf-8')

assert "['region','🌎 Region','#2563eb']" in html, 'Regional tab missing from canonical sections'
assert 'data-nav-key="region"' in app, 'Regional nav key lookup missing from mobile nav controller'
assert "'Region ›'" in app, 'Visible Regional jump cue missing'
assert "scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})" in app, 'Regional jump behavior missing'
assert 'tab-scroll-cue-v2' in app, 'Mobile nav cue controller missing'
assert '.tab-scroll-cue-v2' in css, 'Mobile nav cue styling missing'
assert 'position:sticky' in css, 'Mobile nav cue is not pinned to the visible edge'
assert '.tab-scroll-cue-v2.is-visible' in css, 'Mobile nav cue visible state missing'
assert 'data-region-reachable' not in html, 'Generated HTML must not hard-code runtime reachability state'

print('Mobile Regional navigation visibility contract passed.')
