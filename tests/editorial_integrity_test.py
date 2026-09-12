#!/usr/bin/env python3
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('integrity',ROOT/'scripts/enforce_editorial_integrity.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def item(cat,title,desc='',state=''):
    x=ET.Element('item')
    for tag,val in [('title',title),('description',desc),('category',cat),('state',state),('link','https://example.com/'+str(abs(hash(title)))),('source','Reuters'),('pubDate','Sat, 12 Sep 2026 12:00:00 GMT')]:
        ET.SubElement(x,tag).text=val
    return x

# Domestic U.S. sports/local stories must not survive in World.
a=item('world','How to watch Howard vs Indiana: College football live stream','The Howard Bison face the Indiana Hoosiers in Week 2.','Indiana')
assert m.obvious_domestic_world(a)
b=item('world','At BRICS summit, China, Russia and India urge restraint','Leaders discussed international diplomacy.')
assert not m.obvious_domestic_world(b)

# Related coverage needs concrete event overlap, not a generic actor or broad subject.
p=item('top','CIA releases new records about September 11 attacks')
assert m.related_enough(p,'New CIA records shed light on September 11 attacks')
assert not m.related_enough(p,'White House staff receive holiday gifts from president')

# X topic matching must reject obviously unrelated category/topic combinations.
x=item('x','Caitlin Clark joins USA Basketball training camp','Sports coverage about a basketball player.')
assert not m.x_relevant(x,'World')
science=item('x','NASA telescope study reveals new exoplanet atmosphere','Scientists published new space research.')
assert m.x_relevant(science,'Science')

# Technology commerce and gaming leakage guards.
assert any(term in 'where to preorder the iphone 18 pro' for term in m.TECH_SHOPPING)
assert 'skyrim' in m.GAMING

print('EDITORIAL INTEGRITY TEST PASS')
