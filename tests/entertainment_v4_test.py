#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update_news_v4 as v4

now=datetime.now(timezone.utc)

def item(n, source='Variety', title=None, category='entertainment'):
    return {
        'title': title or f'Actor Person {n} announces new film project',
        'description': f'Actor Person {n} discusses film and entertainment work.',
        'link': f'https://example.com/{n}',
        'source': source,
        'category': category,
        'published': now-timedelta(minutes=n),
        'pubDate': (now-timedelta(minutes=n)).strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }

sample=[item(i, source='Reuters' if i<7 else 'Variety') for i in range(12)]
selected=v4.select_entertainment(sample,limit=10)
assert len(selected)==10, len(selected)
assert all(x.get('entertainmentTier')=='newest' for x in selected[:5])
assert all(x.get('entertainmentTier')=='under-the-radar' for x in selected[5:])
expected=[x['link'] for x in sorted(sample,key=lambda x:x['published'],reverse=True)[:5]]
assert [x['link'] for x in selected[:5]]==expected

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
print('V4 Entertainment tests passed: newest-five ordering, under-the-radar tiering, specialist trust, and red-footnote feed linkage.')
