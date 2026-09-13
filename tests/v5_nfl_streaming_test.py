#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text(encoding='utf-8')
script=(ROOT/'scripts/patch_nfl_streaming.py').read_text(encoding='utf-8')
build=(ROOT/'scripts/build_site.py').read_text(encoding='utf-8')
assert 'function nflStreamingServices(' in html
assert 'class=\\"nfl-airing\\"' in html
assert 'Stream:' in html
for service in ('Netflix','Prime Video','Peacock','Paramount+','ESPN','NFL+','YouTube Sunday Ticket (out-of-market)'):
    assert service in html or service in script, service
assert "'scripts/patch_nfl_streaming.py'" in build
print('V5 NFL broadcast + streaming integration test passed.')
