#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import Counter
from urllib.parse import unquote
import sys
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import update_news_v52 as v52


def make_item(source, rank, hours=1):
    now = datetime.now(timezone.utc)
    return {
        'title': f'{source} story {rank}',
        'description': 'major breaking government policy investigation update',
        'link': f'https://example.com/{source}/{rank}',
        'source': source,
        'category': 'us',
        'published': now - timedelta(hours=hours),
        'pubDate': (now - timedelta(hours=hours)).strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }


def test_constants():
    assert v52.V52_MAX_AGE_HOURS == 336
    assert 'when:14d' in unquote(v52.expanded_feed_url('world news'))
    assert v52.TOP_VISIBLE_SOURCE_CAP == 1
    assert v52.TOP_MID_SOURCE_CAP == 2
    assert v52.TOP_POOL_SOURCE_CAP == 3


def test_first_ten_are_source_diverse():
    pool=[]
    sources=['Reuters','Associated Press','BBC','NPR','NBC News','ABC News','CBS News','CNN','Fox News','USA Today','Politico','The Guardian']
    for i,src in enumerate(sources):
        pool.append(make_item(src,0,hours=i+1))
    for i in range(5):
        pool.append(make_item('Reuters',i+1,hours=1+i))
    ranked=v52.rank_top_pool_v52(pool)
    first10=[v52.source_id(x['source']) for x in ranked[:10]]
    assert len(first10)==10
    assert len(set(first10))==10, first10


def test_best_per_source_leads():
    pool=[make_item('Reuters',0,hours=1),make_item('Reuters',1,hours=20)]
    pool += [make_item(f'Source {i}',0,hours=i+2) for i in range(1,12)]
    ranked=v52.rank_top_pool_v52(pool)
    reuters=[x for x in ranked if v52.source_id(x['source'])=='reuters']
    assert reuters
    assert reuters[0]['link'].endswith('/Reuters/0')


def test_caps_across_pool():
    pool=[]
    for s in range(25):
        source=f'Publisher {s}'
        for i in range(6):
            pool.append(make_item(source,i,hours=(i+s)%48+1))
    ranked=v52.rank_top_pool_v52(pool)
    counts=Counter(v52.source_id(x['source']) for x in ranked)
    assert len(ranked) <= 60
    assert max(counts.values(), default=0) <= 3
    first30=Counter(v52.source_id(x['source']) for x in ranked[:30])
    assert max(first30.values(), default=0) <= 2
    first10=[v52.source_id(x['source']) for x in ranked[:10]]
    assert len(first10)==len(set(first10))


def test_quality_is_modest_tiebreaker():
    now=datetime.now(timezone.utc)
    a=make_item('Reuters',0,1); b=make_item('Unknown Blog',0,1)
    a['published']=b['published']=now-timedelta(hours=1)
    a['title']=b['title']='Government announces major policy change'
    a['description']=b['description']='Breaking national policy update'
    assert v52.top_score(a, now)[0] > v52.top_score(b, now)[0]


if __name__ == '__main__':
    test_constants(); test_first_ten_are_source_diverse(); test_best_per_source_leads(); test_caps_across_pool(); test_quality_is_modest_tiebreaker()
    print('V5.2 patch regressions passed.')
