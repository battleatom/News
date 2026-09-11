#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cluster_political_surfaces as cps
from source_priority import source_priority


def item(cat,title,source,desc,link):
    x=ET.Element('item')
    for tag,val in [
        ('title',title),('link',link),('description',desc),
        ('pubDate','Fri, 11 Sep 2026 12:00:00 GMT'),('source',source),('category',cat)
    ]:
        ET.SubElement(x,tag).text=val
    return x

# Same event entering through adjacent political tabs must collapse.
a=item('us','President proposes $5,000 payments if party wins Congress','Reuters','The president proposed $5,000 payments tied to the same election plan.','a')
b=item('presidential','$5,000 payment promise draws questions','NBC News','The president defended the $5,000 payment proposal tied to the congressional election.','b')
c=item('federal','Lawmakers examine $5,000 payment proposal','CBS News','Congressional lawmakers discussed the same $5,000 payment proposal.','c')
assert cps.cross_same_event(a,b)
assert cps.cross_same_event(a,c)

# Same amount alone is never enough.
d=item('us','Company offers workers a $5,000 signing bonus','USA Today','A private employer announced a $5,000 hiring bonus.','d')
assert not cps.cross_same_event(a,d)

# Primary selection is standards/source-quality first, not political ideology.
assert source_priority('Reuters') > source_priority('Fox News')
assert source_priority('Associated Press') > source_priority('CNN')
assert source_priority('Fox News') == source_priority('CNN')
assert cps.primary_score(a) > cps.primary_score(b)

# Removed cards and their existing coverage links are flattened into the winner.
rel=ET.SubElement(b,'relatedArticles')
old=ET.SubElement(rel,'article')
for tag,val in [('title','Supporting analysis'),('link','support'),('source','BBC')]:
    ET.SubElement(old,tag).text=val
added=cps.attach_all(a,b)
assert added==2
assert len(a.findall('./relatedArticles/article'))==2

print('Political cross-tab clustering tests passed.')
