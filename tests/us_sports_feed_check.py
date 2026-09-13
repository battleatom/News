#!/usr/bin/env python3
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('integrity',ROOT/'scripts/enforce_editorial_integrity.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

root=ET.parse(ROOT/'News').getroot()
channel=root.find('channel')
assert channel is not None
bad_us=[]
bad_world=[]
for item in channel.findall('item'):
    cat=(item.findtext('category') or '').strip().lower()
    if cat=='us':
        action=m.us_sports_disposition(item)
        if action is not None:
            bad_us.append(((item.findtext('title') or '').strip(),action))
    elif cat=='world':
        action=m.world_nfl_disposition(item)
        if action=='nfl':
            bad_world.append((item.findtext('title') or '').strip())
assert not bad_us, f'US sports leakage remains: {bad_us[:10]}'
assert not bad_world, f'NFL headlines remain in World: {bad_world[:10]}'
print('US/WORLD SPORTS FEED CHECK PASS')
