#!/usr/bin/env python3
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import event_consolidate as ec


def add(channel,title,link,source='Publisher',category='us',desc=''):
    item=ET.SubElement(channel,'item')
    for tag,val in [('title',title),('link',link),('source',source),('category',category),('description',desc),('pubDate','Fri, 11 Sep 2026 12:00:00 GMT')]:
        ET.SubElement(item,tag).text=val
    return item


def make_feed(path,rows):
    rss=ET.Element('rss'); channel=ET.SubElement(rss,'channel')
    for row in rows:add(channel,*row)
    ET.ElementTree(rss).write(path,encoding='utf-8',xml_declaration=True)

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'News'
    make_feed(p,[
        ('President proposes $5,000 support payment for households','https://a.test/1','A','us','A proposed $5,000 payment would go to qualifying households.'),
        ('Details emerge on $5,000 household support payment proposal','https://b.test/2','B','us','Officials discussed the same $5,000 support payment for households.'),
        ('President meets technology executives on chip policy','https://c.test/3','C','us','Separate technology policy meeting.'),
        ('Communities mark 9/11 anniversary with memorial events','https://d.test/4','D','us','September 11 memorial events are being held.'),
        ('9/11 anniversary ceremonies honor victims nationwide','https://e.test/5','E','us','Memorial ceremonies mark September 11.'),
    ])
    result=ec.run(p)
    out=ET.parse(p).getroot().findall('.//item')
    assert result['removed']==2,result
    assert len(out)==3,len(out)
    related=sum(len(x.findall('relatedArticles/article')) for x in out)
    assert related==2,related
    titles=[x.findtext('title') for x in out]
    assert any('technology executives' in t for t in titles),titles

print('Generic event consolidation tests passed.')
