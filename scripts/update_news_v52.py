#!/usr/bin/env python3
"""V5.2 experimental collector wrapper.

Production V5.1 remains untouched. V5.2 expands normal discovery to 14 days,
adds source-quality/diversity to Top Stories, and deliberately exhausts trusted
fallback rosters for source-heavy categories so final ranking has real publisher
choice instead of stopping after the first source fills the pool.
"""
from __future__ import annotations
import re,urllib.parse
from collections import Counter,defaultdict
import update_news_v4 as v4

core=v4.core
V52_MAX_AGE_HOURS=14*24
TOP_POOL_SIZE=60
TOP_POOL_SOURCE_CAP=3

V52_TOP_SOURCE_QUERIES=[
('Bloomberg','site:bloomberg.com breaking world US politics economy news'),('CNBC','site:cnbc.com breaking US world politics economy news'),
('Politico','site:politico.com breaking US politics government news'),('The Hill','site:thehill.com breaking US politics government news'),
('Axios','site:axios.com breaking US politics world business news'),('The Guardian','site:theguardian.com breaking world US politics news'),
('PBS NewsHour','site:pbs.org/newshour breaking US world politics news'),('Al Jazeera','site:aljazeera.com breaking world international US news'),
('Financial Times','site:ft.com world US politics economy breaking news'),('TIME','site:time.com US world politics breaking news')]

SOURCE_QUALITY={'reuters':20,'associatedpress':20,'ap':20,'afp':19,'bbc':18,'npr':18,'pbsnewshour':17,'bloomberg':17,'newyorktimes':16,'washingtonpost':16,'financialtimes':16,'nbcnews':15,'abcnews':15,'cbsnews':15,'cnbc':15,'axios':15,'politico':14,'cnn':14,'foxnews':14,'aljazeera':14,'usatoday':13,'guardian':13,'thehill':12,'time':12,'espn':14,'nflcom':15,'cbssports':14,'nbcsports':14,'foxsports':14,'yahoosports':12,'theverge':14,'arstechnica':15,'techcrunch':12,'wired':13,'defensenews':14,'militarytimes':13,'breakingdefense':14,'variety':14,'hollywoodreporter':14,'deadline':13,'billboard':13,'sourcenewmexico':15,'newmexicoindepth':15,'albuquerquejournal':14,'santafenewmexican':14,'tricityrecord':14,'durangoherald':13,'navajotimes':14}

def source_id(value):
    raw=re.sub(r'[^a-z0-9]+','',(value or '').lower())
    if raw.startswith('the') and raw[3:] in SOURCE_QUALITY:raw=raw[3:]
    if raw.startswith('associatedpress'):return 'associatedpress'
    if raw.startswith('reuters'):return 'reuters'
    if raw.startswith('bbc'):return 'bbc'
    return raw or 'unknown'
def source_quality(item):return SOURCE_QUALITY.get(source_id(item.get('source') or ''),8)
def expanded_feed_url(query):
    q=urllib.parse.quote(f'{query} when:14d');return f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'
def _related_source_count(item):
    s={source_id(item.get('source') or '')}
    for rel in item.get('_relatedArticles',[]) or []:s.add(source_id(rel.get('source') or ''))
    s.discard('unknown');return max(1,len(s))
def top_score(item,newest):
    impact=core.impact_score(item,newest);confirm=min(20,max(0,_related_source_count(item)-1)*5)
    return (impact+confirm+source_quality(item),item.get('published'))
def rank_top_pool_v52(base_pool):
    if not base_pool:return []
    newest=max(x['published'] for x in base_pool);ranked=sorted(base_pool,key=lambda x:top_score(x,newest),reverse=True)
    buckets=defaultdict(list);seen=set()
    for item in ranked:
        k=core.key(item)
        if not k or k in seen:continue
        seen.add(k);buckets[source_id(item.get('source') or '')].append(item)
    selected=[]
    for r in range(TOP_POOL_SOURCE_CAP):
        round_items=[b[r] for b in buckets.values() if len(b)>r];round_items.sort(key=lambda x:top_score(x,newest),reverse=True)
        for item in round_items:
            if len(selected)>=TOP_POOL_SIZE:return selected
            selected.append(item)
    return selected

_original_select_top=core.select_top_stories
def select_top_stories_v52(unique):
    base=_original_select_top(unique);selected=rank_top_pool_v52(base);counts=Counter(source_id(x.get('source') or '') for x in selected)
    first10=[source_id(x.get('source') or '') for x in selected[:10]];all_sources={source_id(x.get('source') or '') for x in selected};first_round=[source_id(x.get('source') or '') for x in selected[:len(all_sources)]]
    print(f'V5.2 TOP diversity: {len(set(first10))}/{len(first10)} distinct sources in first 10; {len(set(first_round))}/{len(first_round)} distinct in source round 1; max source count {max(counts.values(),default=0)} across {len(selected)} retained stories.')
    return selected

_existing={n.lower() for n,_ in core.MAINSTREAM_TOP_QUERIES}
for n,q in V52_TOP_SOURCE_QUERIES:
    if n.lower() not in _existing:core.MAINSTREAM_TOP_QUERIES.append((n,q));_existing.add(n.lower())

core.MAX_AGE_HOURS=V52_MAX_AGE_HOURS
core.feed_url=expanded_feed_url
core.select_top_stories=select_top_stories_v52

# V5.1 normally stops fallback discovery as soon as one publisher can satisfy a
# category target. V5.2 deliberately makes the target unreachable for categories
# with trusted multi-source rosters, causing the collector to query the full roster.
# The normal final pool caps still apply later, so this expands candidate diversity
# without expanding what the user sees.
for _cat in ('world','us','presidential','federal','nm','nfl','technology','gaming','military'):
    if _cat in core.TRUSTED_CATEGORY_FALLBACKS:
        core.CATEGORY_POOL_MINIMUMS[_cat]=999

def main():v4.main()
if __name__=='__main__':main()
