#!/usr/bin/env python3
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('nfl_guard', ROOT / 'scripts/enforce_nfl_final.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def item(title, desc=''):
    x = ET.Element('item')
    ET.SubElement(x, 'title').text = title
    ET.SubElement(x, 'description').text = desc
    ET.SubElement(x, 'category').text = 'nfl'
    return x

assert not m.nfl_relevant(item("Ukraine’s biggest victory this year exposes lying Russian commanders")), 'foreign commanders leak survived NFL guard'
assert not m.nfl_relevant(item('Russian commanders order retreat near Ukraine front', 'Military officials described the battle.'))
assert m.nfl_relevant(item('Washington Commanders make late roster move'))
assert m.nfl_relevant(item('Commanders make late roster move', 'The NFL team adjusted its roster before kickoff.'))
assert m.nfl_relevant(item('Chiefs rally late to beat Chargers'))

print('NFL FINAL GUARD TEST PASS')
