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
# A 72-hour THR lead can still participate because V5.1 treats <=72h as fresh; NBC/USA Today
# follow-up also keeps this event current and source-diverse.
sydney=[
    item(1,'Sydney Sweeney faces backlash over controversial sports ad','The Hollywood Reporter',72*60),
    item(2,"Female athletes hit back at Sydney Sweeney's controversial sports ad",'NBC News',16*60),
    item(3,'Sydney Sweeney sports ad draws backlash from female athletes','USA Today',20*60),
]
routine=item(4,'Actor Example joins new streaming series','Variety',5)
ranked=r.rank_events(sydney+[routine],limit=5,now=now)
assert ranked[0]['entertainmentCoverage']>=2, ranked[0]
assert 'Sydney Sweeney' in ranked[0]['title'], ranked[0]['title']
assert len([x for x in ranked if 'Sydney Sweeney' in x['title']])==1
related_titles=' '.join(x.get('title','') for x in ranked[0].get('_relatedArticles',[]))
assert 'Sydney Sweeney' in related_titles, ranked[0]

# A story inside the 7-day lookback but outside the 72-hour freshness window must not publish
# by itself. It needs fresh same-event coverage to qualify as an older lead.
stale=item(9,'Actor Stale Example announces surprise project','Variety',73*60)
assert not r.rank_events([stale],limit=3,now=now)

# A story beyond the V5.1 168-hour lookback is always excluded.
too_old=item(15,'Actor Very Old Example announces archival project','Variety',169*60)
assert not r.rank_events([too_old],limit=3,now=now)

# Generic coverage of one awards ceremony collapses into one event lead + supporting coverage.
emmys=[
    item(5,'Emmy Awards 2026: What to expect from the ceremony and how to watch','BBC',90),
    item(6,'How to watch the 2026 Emmy Awards','CBS News',40),
    item(10,"'The Pitt' and 'Hacks' compete for gold at TV's Emmy Awards",'Reuters',60),
    item(11,'Emmys 2026: Seen and Heard at Every Star-Studded Party','The Hollywood Reporter',20),
]
ranked2=r.rank_events(emmys+[routine],limit=5,now=now)
emmy_rows=[x for x in ranked2 if 'emmy' in x['title'].lower()]
assert len(emmy_rows)==1, [x['title'] for x in emmy_rows]
assert emmy_rows[0]['entertainmentLabel']=='AWARDS', emmy_rows[0]
assert emmy_rows[0]['entertainmentCoverage']>=3, emmy_rows[0]

# Listicle/gallery/section clutter is not a top-news card.
listicle=item(12,'15 Stars Who Brought Their Parents as Awards Show Dates','People',15)
assert not r.relevant(listicle)
shocking=item(13,'The 10 Most Shocking Moments in Emmys History','InStyle',15)
assert not r.relevant(shocking)
landing=item(14,'Film + Reviews - The Guardian','The Guardian',10)
assert not r.relevant(landing)

# People/family/relationship coverage is valid normal Entertainment, not a hidden Dirty pool.
divorce=item(7,"Reacher star Alan Ritchson divorce revealed in court documents",'People',120)
assert r.relevant(divorce)
assert r.importance(divorce)[1] in {'MAJOR','PEOPLE'}

# Explicit adult-industry material never enters the pool.
adult=item(8,'Adult film star announces OnlyFans project','Example Source',10)
assert not r.relevant(adult)

print('Entertainment ranking regression passed: V5.1 72h freshness and 168h lookback are enforced, fresh multi-source events can carry older supporting coverage, award megastories collapse, listicles/landing pages are rejected, and adult content is rejected.')
