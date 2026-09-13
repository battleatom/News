#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import enrich_x_issues as xissues
import enforce_editorial_integrity as integrity

items=ET.parse(ROOT/'News').getroot().findall('./channel/item')
x=[i for i in items if integrity.text(i,'category').lower()=='x']
topics=[integrity.text(i,'xTopic') for i in x]
assert topics==xissues.EXPECTED_TOPICS, (topics,xissues.EXPECTED_TOPICS)
assert len(x)==10 and len(set(topics))==10
for item,topic in zip(x,topics):
    assert integrity.x_relevant(item,topic), (topic,integrity.text(item,'title'))
    assert integrity.text(item,'title') and integrity.text(item,'link') and integrity.text(item,'source')
print('V5 X feed integrity passed for all 10 fixed topics.')
