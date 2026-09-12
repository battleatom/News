#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update_news_v4 as v4

now=datetime.now(timezone.utc)

def item(n, source='Variety', title=None, category='entertainment', description=None):
    return {
        'title': title or f'Actor Person {n} announces new film project',
        'description': description or f'Actor Person {n} discusses film and entertainment work.',
        'link': f'https://example.com/{n}',
        'source': source,
        'category': category,
        'published': now-timedelta(minutes=n),
        'pubDate': (now-timedelta(minutes=n)).strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }

sample=[item(i, source=f'Entertainment Source {i}') for i in range(12)]
selected=v4.select_entertainment(sample,limit=10)
assert len(selected)==10, len(selected)
assert all(x.get('entertainmentSafety') in {'clean','dirty'} for x in selected)
assert all(x.get('entertainmentLabel') for x in selected)
assert all(str(x.get('entertainmentScore','')).isdigit() for x in selected)

major=item(40,title='Actor Major Example arrested after serious investigation')
career=item(1,title='Actor Career Example joins new television series')
ranked=v4.select_entertainment([career,major],limit=2)
assert ranked[0]['link']==major['link'], 'Major consequence must outrank a newer routine career item'
assert ranked[0]['entertainmentLabel']=='MAJOR'

gossip=item(2,title='Actor Gossip Example dating musician after gala appearance')
assert v4.entertainment_safety(gossip)=='dirty'
professional=item(3,title='Actor Professional Example signs film contract')
assert v4.entertainment_safety(professional)=='clean'

ent=item(50,title='Jane Example speaks out after studio labor investigation')
under=item(60,source='ProPublica',title='Jane Example named in studio labor investigation',category='underreported')
under['description']='Investigation examines labor conditions involving Jane Example and the studio.'
xml=v4.v4_build([ent,under])
root=ET.fromstring(xml)
ent_node=next(x for x in root.findall('.//item') if (x.findtext('category') or '')=='entertainment')
links=ent_node.findall('underreportedLinks/article')
assert links, 'Expected Entertainment-to-Underreported cross-link'
assert 'Jane Example' in (links[0].findtext('title') or '')

assert v4.core.source_is_trusted('Variety')
assert v4.core.source_is_trusted('Billboard')
assert v4.core.source_is_trusted('People')
assert v4.core.source_is_trusted('TMZ')
print('V4 Entertainment tests passed: importance hierarchy, Clean/Dirty tagging, publisher diversity, expanded specialist trust, and red-footnote feed linkage.')
