from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
html=(ROOT/'index.html').read_text(encoding='utf-8')
build=(ROOT/'scripts'/'build_site.py').read_text(encoding='utf-8')

assert "scripts/patch_nfl_streaming.py',\n    'scripts/patch_nfl_live_center.py'" in build, 'Live center must run after NFL streaming patch'
assert '/* nfl-live-center-v1 */' in html, 'NFL live center CSS missing from generated page'
assert "liveCenter.className='nfl-live-center'" in html, 'NFL live center DOM missing'
assert 'await renderLivePlayCenter(events);' in html, 'NFL live center is not tied to scoreboard refresh'
assert 'summary?event=' in html, 'NFL live center summary/play-by-play endpoint missing'
assert 'slice(-4).reverse()' in html, 'NFL live center should display only the latest compact play set'
assert 'overflow:visible!important;max-height:none!important' in html, 'NFL play-by-play must not use an internal scroll region'
assert '.nfl-live-center[hidden]{display:none!important}' in html, 'Live center must disappear when no game is live'
assert "if(!live.length){liveCenter.hidden=true" in html, 'No-live-game behavior missing'
assert 'Game pulse' in html, 'Factual live commentary pulse missing'
assert 'nfl-games-grid' in html, 'Existing NFL score cards were lost'
assert 'nfl-stream' in html, 'Existing NFL streaming metadata was lost'

print('NFL live play-by-play center contract passed.')
