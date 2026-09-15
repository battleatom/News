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
    assert v52.TOP_POOL_SOURCE_CAP == 3
    assert len(v52.V52_TOP_SOURCE_QUERIES) >= 8
    assert len(v52.core.MAINSTREAM_TOP_QUERIES) >= 20


def test_first_round_is_one_per_source():
    pool=[]
    sources=['Reuters','Associated Press','BBC','NPR','NBC News','ABC News','CBS News','CNN','Fox News','USA Today','Politico','The Guardian']
    for i,src in enumerate(sources):
        for rank in range(4):
            pool.append(make_item(src,rank,hours=i+rank+1))
    ranked=v52.rank_top_pool_v52(pool)
    first_round=[v52.source_id(x['source']) for x in ranked[:len(sources)]]
    assert len(first_round)==len(sources)
    assert len(set(first_round))==len(sources), first_round
    first10=first_round[:10]
    assert len(set(first10))==10


def test_best_per_source_leads():
    sources=['Reuters']+[f'Source {i}' for i in range(1,12)]
    pool=[]
    for source in sources:
        pool.append(make_item(source,0,hours=1))
        pool.append(make_item(source,1,hours=20))
    ranked=v52.rank_top_pool_v52(pool)
    first_round=ranked[:len(sources)]
    assert all(x['link'].endswith('/0') for x in first_round)


def test_round_robin_and_full_cap():
    pool=[]
    sources=[f'Publisher {s}' for s in range(25)]
    for s,source in enumerate(sources):
        for i in range(6):
            pool.append(make_item(source,i,hours=(i+s)%48+1))
    ranked=v52.rank_top_pool_v52(pool)
    counts=Counter(v52.source_id(x['source']) for x in ranked)
    assert len(ranked)==60
    assert max(counts.values(), default=0) <= 3
    # Round one is complete before any publisher receives a second card.
    first_round=[v52.source_id(x['source']) for x in ranked[:25]]
    assert len(set(first_round))==25
    # Round two is complete before round three starts; first 50 have max two/source.
    first_two=Counter(v52.source_id(x['source']) for x in ranked[:50])
    assert max(first_two.values())==2


def test_quality_is_modest_tiebreaker():
    now=datetime.now(timezone.utc)
    a=make_item('Reuters',0,1); b=make_item('Unknown Blog',0,1)
    a['published']=b['published']=now-timedelta(hours=1)
    a['title']=b['title']='Government announces major policy change'
    a['description']=b['description']='Breaking national policy update'
    assert v52.top_score(a, now)[0] > v52.top_score(b, now)[0]


if __name__ == '__main__':
    test_constants(); test_first_round_is_one_per_source(); test_best_per_source_leads(); test_round_robin_and_full_cap(); test_quality_is_modest_tiebreaker()
    print('V5.2 patch regressions passed.')
