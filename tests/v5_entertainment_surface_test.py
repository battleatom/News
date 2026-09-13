#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
asset=(ROOT/'assets/entertainment-v4.js').read_text(encoding='utf-8')
html=(ROOT/'index.html').read_text(encoding='utf-8')
assert "const DIRTY_UI_ENABLED=false;" in asset
assert "return 'clean';" in asset
assert "No verified entertainment stories are available right now." in asset
assert html.count('assets/entertainment-v4.js')==1
print('V5 Entertainment clean-surface integration test passed.')
