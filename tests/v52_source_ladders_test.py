#!/usr/bin/env python3
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import v52_source_ladders as m


def item(title,source,cat='gaming',desc='Detailed reporting explains what happened, why it matters, who is affected, and the concrete consequences of the event in enough depth to be useful.',hours=0,url=None):
    x=ET.Element('item')
    for k,v in {
        'title':title,'source':source,'category':cat,'description':desc,
        'published':(datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat(),
        'link':url or ('https://example.com/'+str(abs(hash((title,source)))))
    }.items(): ET.SubElement(x,k).text=v
    return x


def titles(rows): return [m.headline(x) for x in rows]


def test_gaming_rounds():
    rows=[
        item('IGN first major game announcement','IGN'),
        item('IGN second major game announcement','IGN',hours=1),
        item('PlayStation first platform game announcement','PlayStation Blog'),
        item('PlayStation second platform game announcement','PlayStation Blog',hours=1),
        item('Nintendo first Switch game announcement','Nintendo'),
        item('Nintendo second Switch game announcement','Nintendo',hours=1),
        item('Independent backup publisher game announcement','Unknown Gaming Wire'),
    ]
    out,rejected,sources=m.ladder(rows,'gaming')
    assert not rejected
    first_round=[x for x in out if m.field(x,'v52SelectionRound')=='1']
    assert [m.norm_source(m.field(x,'source')) for x in first_round[:3]] == ['ign','playstationblog','nintendo']
    assert m.norm_source(m.field(first_round[-1],'source'))=='unknowngamingwire'
    # Second story from IGN must not appear before first stories from PlayStation/Nintendo.
    assert titles(out).index('IGN second major game announcement') > titles(out).index('Nintendo first Switch game announcement')


def test_duplicate_promotes_next_story():
    rows=[
        item('PlayStation announces major PS5 system update','IGN',url='https://ign.com/a'),
        item('PlayStation announces major PS5 system update today','GameSpot',url='https://gamespot.com/a'),
        item('GameSpot covers a different Xbox release','GameSpot',url='https://gamespot.com/b'),
    ]
    out,rejected,_=m.ladder(rows,'gaming')
    assert len(out)==2
    assert any(reason=='near-duplicate' for _,reason in rejected)
    assert 'GameSpot covers a different Xbox release' in titles(out)


def test_short_title_requires_content():
    weak=item('Big change','IGN',desc='Tiny blurb.')
    strong=item('Big change','IGN',desc='Nintendo detailed a major platform update affecting millions of Switch players, including performance changes, compatibility details, release timing, and developer requirements. The explanation is specific enough to identify the event and its consequences.')
    assert m.content_sufficient(weak)[0] is False
    assert m.content_sufficient(strong)[0] is True


def test_underreported_not_in_hierarchy():
    assert 'underreported' not in m.HIERARCHIES


def test_each_tab_has_unique_hierarchy():
    required={'top','world','us','presidential','federal','legislation','nm','local','region','nfl','technology','gaming','military','entertainment'}
    assert required <= set(m.HIERARCHIES)
    for cat in required:
        vals=[m.norm_source(x) for x in m.HIERARCHIES[cat]]
        assert len(vals)==len(set(vals)), cat


if __name__=='__main__':
    test_gaming_rounds();test_duplicate_promotes_next_story();test_short_title_requires_content();test_underreported_not_in_hierarchy();test_each_tab_has_unique_hierarchy()
    print('V5.2 B2 source ladder contracts passed')
