#!/usr/bin/env python3
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

spec=importlib.util.spec_from_file_location('integrity',ROOT/'scripts/enforce_editorial_integrity.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import classify_live_feed as classifier
from filter_landing_pages import is_landing_page


def item(cat,title,desc='',state='',source='Reuters'):
    x=ET.Element('item')
    for tag,val in [('title',title),('description',desc),('category',cat),('state',state),('link','https://example.com/'+str(abs(hash(title)))),('source',source),('pubDate','Sat, 12 Sep 2026 12:00:00 GMT')]:
        ET.SubElement(x,tag).text=val
    return x

# Domestic U.S. sports/local stories must not survive in World.
a=item('world','How to watch Howard vs Indiana: College football live stream','The Howard Bison face the Indiana Hoosiers in Week 2.','Indiana')
assert m.obvious_domestic_world(a)
b=item('world','At BRICS summit, China, Russia and India urge restraint','Leaders discussed international diplomacy.')
assert not m.obvious_domestic_world(b)

# A foreign cultural reference must not make a clearly domestic event a World story.
mn=item('world','A little bit of Germany here in Minnesota','A German-American institute is holding an Oktoberfest celebration in St. Paul.')
assert m.obvious_domestic_world(mn), 'Minnesota cultural event incorrectly survives as World'

# User-reported domain leakage: strong headline evidence should beat the broad World prior.
game=item('world',"'StarCraft 3,' an Open-World Shooter Game Coming in 2030; First Look Revealed",'A publisher revealed a new StarCraft game.')
gd=classifier.classify(game)
assert gd['action']=='reroute' and gd['category']=='gaming' and gd['confidence']>=0.80, gd

ai=item('world','Two of the world’s top AI chief executives publicly agree on slowing AI development','Anthropic executives discussed slowing artificial intelligence development.')
ad=classifier.classify(ai)
assert ad['action']=='reroute' and ad['category']=='technology' and ad['confidence']>=0.80, ad

# Generic broadcast/program/roundup pages are not event-specific news. Short event
# headlines remain valid; there is deliberately no minimum word-count rule.
for generic in (
    'Local 10 World News @06:30 PM',
    'The National News Desk Weekend Edition',
    'The News Roundup For September 11, 2026 : 1A',
):
    assert is_landing_page(item('world',generic)), generic
assert not is_landing_page(item('world','Russia destroys hospital')), 'short event headline was over-filtered'

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
