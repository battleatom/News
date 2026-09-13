#!/usr/bin/env python3
import json, sys, tempfile, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from article_type import classify_article_type
from v51_policy import overlap_allowed, FAST_LANE, SLOW_LANE
import cross_tab_integrity_fast as dedupe
import source_health, collect_direct_rss

assert classify_article_type('Undercover Cops Review for Arcade Games','','https://example.com/reviews/1')=='review'
assert classify_article_type('How to find every secret level')=='guide'
assert classify_article_type('Top 10 RPG games')=='listicle'
assert classify_article_type('Nintendo announces new Switch hardware')=='news'
assert overlap_allowed('presidential','federal')
assert overlap_allowed('world','military')
assert not overlap_allowed('world','gaming')
assert FAST_LANE.isdisjoint(SLOW_LANE)

def mk(cat,title,link,resolved=''):
    i=ET.Element('item')
    for tag,val in [('category',cat),('title',title),('link',link),('description','A sufficiently detailed description about the same underlying event and reporting.')]: ET.SubElement(i,tag).text=val
    if resolved: ET.SubElement(i,'resolvedPublisherUrl').text=resolved
    return i
one=mk('us','Major court ruling changes policy today','https://news.google.com/a','https://example.com/story?utm_source=x&id=7')
two=mk('world','Major court ruling changes policy today','https://news.google.com/b','https://www.example.com/story?id=7&utm_medium=y')
groups,_=dedupe.scan([one,two]); assert groups, 'canonical publisher URL should dedupe wrappers'
three=mk('federal','White House policy shift','https://x','https://example.com/policy')
four=mk('presidential','White House policy shift','https://y','https://example.com/policy')
groups,_=dedupe.scan([three,four]); assert not groups

with tempfile.TemporaryDirectory() as td:
    root=ET.Element('rss'); ch=ET.SubElement(root,'channel')
    for n,(cat,src) in enumerate([('world','Reuters'),('world','BBC'),('us','AP'),('us','Reuters')]):
        i=ET.SubElement(ch,'item'); ET.SubElement(i,'title').text=f'Story {n}'; ET.SubElement(i,'category').text=cat; ET.SubElement(i,'source').text=src
    feed=Path(td)/'News'; out=Path(td)/'health.json'; ET.ElementTree(root).write(feed,encoding='utf-8',xml_declaration=True)
    report=source_health.run(feed,out); assert report['distinctSources']==3 and out.exists()

# Direct RSS augmentation is deterministic under a fixture and ignores tracking wrappers.
with tempfile.TemporaryDirectory() as td:
    root=ET.Element('rss'); ch=ET.SubElement(root,'channel'); feed=Path(td)/'News'; ET.ElementTree(root).write(feed,encoding='utf-8',xml_declaration=True)
    registry=Path(td)/'registry.json'; registry.write_text(json.dumps({'sources':[{'name':'Fixture News','scope':['technology'],'defaultCategory':'technology','directRss':'https://fixture.invalid/rss'}]}),encoding='utf-8')
    report=Path(td)/'direct.json'
    xml=b'''<rss><channel><item><title>Fixture publisher announces AI platform</title><link>https://example.com/a?utm_source=rss</link><description>Company announces a new AI platform.</description><pubDate>Sat, 13 Sep 2026 18:00:00 GMT</pubDate></item></channel></rss>'''
    old=collect_direct_rss.fetch; collect_direct_rss.fetch=lambda url: xml
    try: result=collect_direct_rss.run(feed,registry,report)
    finally: collect_direct_rss.fetch=old
    assert result['added']==1 and report.exists()
    item=ET.parse(feed).getroot().find('.//item'); assert item.findtext('collectorSource')=='direct-rss' and item.findtext('category')=='technology'
print('V5.1 architecture test passed.')
