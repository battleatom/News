#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import refine_entertainment as r

now=datetime.now(timezone.utc)

def item(i,title,source='Variety',minutes=30,description='Entertainment coverage'):
    return {
        'title':title,
        'description':description,
        'link':f'https://example.com/{i}',
        'source':source,
        'category':'entertainment',
        'published':now-timedelta(minutes=minutes),
        'pubDate':(now-timedelta(minutes=minutes)).strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }

# Multi-source current event should beat a routine single-source story and collapse to one lead.
sydney=[
    item(1,'Sydney Sweeney faces backlash over controversial sports ad','The Hollywood Reporter',20),
    item(2,"Female athletes hit back at Sydney Sweeney's controversial sports ad",'NBC News',40),
    item(3,'Sydney Sweeney sports ad draws backlash from female athletes','USA Today',55),
]
routine=item(4,'Actor Example joins new streaming series','Variety',5)
ranked=r.rank_events(sydney+[routine],limit=5,now=now)
assert ranked[0]['entertainmentCoverage']>=2, ranked[0]
assert 'Sydney Sweeney' in ranked[0]['title'], ranked[0]['title']
assert len([x for x in ranked if 'Sydney Sweeney' in x['title']])==1
assert len(ranked[0].get('_relatedArticles',[]))>=1

# Current awards coverage should remain highly ranked.
emmys=[
    item(5,'Emmy Awards 2026: What to expect from the ceremony and how to watch','BBC',90),
    item(6,'How to watch the 2026 Emmy Awards','CBS News',40),
]
ranked2=r.rank_events(emmys+[routine],limit=3,now=now)
assert ranked2[0]['entertainmentLabel']=='AWARDS', ranked2[0]

# People/family/relationship coverage is valid normal Entertainment, not a hidden Dirty pool.
divorce=item(7,"Reacher star Alan Ritchson divorce revealed in court documents",'People',120)
assert r.relevant(divorce)
assert r.importance(divorce)[1] in {'MAJOR','PEOPLE'}

# Explicit adult-industry material never enters the pool.
adult=item(8,'Adult film star announces OnlyFans project','Example Source',10)
assert not r.relevant(adult)

print('Entertainment ranking regression passed: current multi-source events outrank routine singles, duplicates collapse with supporting links, and adult content is rejected.')
