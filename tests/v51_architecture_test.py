#!/usr/bin/env python3
import sys, tempfile, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from article_type import classify_article_type
from v51_policy import overlap_allowed, FAST_LANE, SLOW_LANE
import cross_tab_integrity_fast as dedupe
import source_health

assert classify_article_type('Undercover Cops Review for Arcade Games','','https://example.com/reviews/1')=='review'
assert classify_article_type('How to find every secret level')=='guide'
assert classify_article_type('Top 10 RPG games')=='listicle'
assert classify_article_type('Nintendo announces new Switch hardware')=='news'
assert overlap_allowed('presidential','federal')
assert overlap_allowed('world','military')
assert not overlap_allowed('world','gaming')
assert FAST_LANE.isdisjoint(SLOW_LANE)

# Publisher URL must win over Google wrapper URL and tracking parameters must collapse.
def mk(cat,title,link,resolved=''):
    i=ET.Element('item')
    for tag,val in [('category',cat),('title',title),('link',link),('description','A sufficiently detailed description about the same underlying event and reporting.')]: ET.SubElement(i,tag).text=val
    if resolved: ET.SubElement(i,'resolvedPublisherUrl').text=resolved
    return i
one=mk('us','Major court ruling changes policy today','https://news.google.com/a','https://example.com/story?utm_source=x&id=7')
two=mk('world','Major court ruling changes policy today','https://news.google.com/b','https://www.example.com/story?id=7&utm_medium=y')
groups,_=dedupe.scan([one,two]); assert groups, 'canonical publisher URL should dedupe wrappers'
# Allowed overlap stays separate even for identical canonical URL.
three=mk('federal','White House policy shift','https://x','https://example.com/policy')
four=mk('presidential','White House policy shift','https://y','https://example.com/policy')
groups,_=dedupe.scan([three,four]); assert not groups

with tempfile.TemporaryDirectory() as td:
    root=ET.Element('rss'); ch=ET.SubElement(root,'channel')
    for n,(cat,src) in enumerate([('world','Reuters'),('world','BBC'),('us','AP'),('us','Reuters')]):
        i=ET.SubElement(ch,'item'); ET.SubElement(i,'title').text=f'Story {n}'; ET.SubElement(i,'category').text=cat; ET.SubElement(i,'source').text=src
    feed=Path(td)/'News'; out=Path(td)/'health.json'; ET.ElementTree(root).write(feed,encoding='utf-8',xml_declaration=True)
    report=source_health.run(feed,out); assert report['distinctSources']==3 and out.exists()
print('V5.1 architecture test passed.')
