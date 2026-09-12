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
bad=[]
for item in channel.findall('item'):
    cat=(item.findtext('category') or '').strip().lower()
    if cat!='us':
        continue
    action=m.us_sports_disposition(item)
    if action is not None:
        bad.append(((item.findtext('title') or '').strip(),action))
assert not bad, f'US sports leakage remains: {bad[:10]}'
print('US SPORTS FEED CHECK PASS')
