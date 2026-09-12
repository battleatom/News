#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import html as html_lib
import re
import xml.etree.ElementTree as ET

import update_news_v4 as v4

core=v4.core
NEWS=Path('News')

# Professional/general Entertainment sources.
PREVIEW_SOURCES=[
    ('People','site:people.com celebrity actor actress dating relationship baby wedding fashion charity'),
    ('TMZ','site:tmz.com celebrity actor actress dating fashion adult film star'),
    ('E! News','site:eonline.com celebrity actor actress dating relationship fashion red carpet'),
    ('Variety','site:variety.com actor actress Hollywood television film entertainment'),
    ('Billboard','site:billboard.com music artist singer rapper tour album'),
    ('Deadline','site:deadline.com actor actress television film Hollywood'),
]

# These are intentionally Dirty-mode-only pools. The query is narrow enough that
# stories from these batches are explicitly tagged broad/dirty even when the title
# itself omits words such as "adult" or "nude".
DIRTY_PREVIEW_SOURCES=[
    ('AVN','site:avn.com adult entertainment industry performer actress actor awards business'),
    ('XBIZ','site:xbiz.com adult entertainment industry performer actress actor awards business'),
    ('Page Six','site:pagesix.com celebrity nude naked topless bikini swimsuit sheer see-through dating romance'),
    ('Us Weekly','site:usmagazine.com celebrity bikini swimsuit sheer nude dating breakup pregnancy baby'),
    ('People','site:people.com celebrity bikini swimsuit sheer nude dating relationship pregnancy baby philanthropy'),
    ('E! News','site:eonline.com celebrity bikini swimsuit sheer nude dating breakup red carpet fashion'),
]

ADULT_TRADE_SOURCES={'avn','xbiz'}
DIRTY_RESERVE=8
ADULT_RESERVE=4

# Dirty mode is meant to cover adult performers/industry, not become an explicit
# content feed. These terms remove overt scene/product promotion from the direct
# trade fallback while retaining performer, awards, legal, business and platform news.
XBIZ_EXPLICIT_SKIP=(
    'gangbang','anal scene','first anal','sex toy','stroker','dildo','sex doll',
    'masturbator','porn scene','hardcore','blowjob','oral scene','double penetration',
)
XBIZ_KEEP_HINTS=(
    'performer','star','actress','actor','award','wins','winner','featured','feature',
    'interview','podcast','launch','platform','business','company','studio','industry',
    'legal','lawsuit','court','regulation','compliance','creator','onlyfans','fansly',
    'model','agency','director','producer','executive','joins','hired','signs','deal',
    'event','conference','expands','expansion','partnership','acquires','acquisition',
)


def _key(item):
    try:
        return core.key(item)
    except Exception:
        return (item.get('link') or item.get('title') or '').strip().lower()


def _decorate_dirty(item, adult_trade=False):
    copy=dict(item)
    score,label=v4.entertainment_importance(copy)
    copy['entertainmentSafety']='dirty'
    copy['entertainmentLabel']='ADULT INDUSTRY' if adult_trade else label
    copy['entertainmentScore']=max(280 if adult_trade else 220,score if label in {'MAJOR','CAREER'} else 0)
    copy['entertainmentTier']='under-the-radar'
    # Never render source thumbnails for adult-industry reserve stories.
    if adult_trade:
        copy['imageUrl']=''
    return copy


def _newest_distinct(items, limit):
    out=[];seen=set()
    for item in sorted(items,key=lambda x:x.get('published') or datetime.min.replace(tzinfo=timezone.utc),reverse=True):
        k=_key(item)
        if not k or k in seen:
            continue
        title=(item.get('title') or '').lower()
        desc=(item.get('description') or '').lower()
        if any(term in f'{title} {desc}' for term in v4.ENTERTAINMENT_REJECT_TERMS):
            continue
        seen.add(k);out.append(item)
        if len(out)>=limit:
            break
    return out


def _strip_tags(value):
    value=re.sub(r'<[^>]+>',' ',value or '')
    value=html_lib.unescape(value)
    return re.sub(r'\s+',' ',value).strip()


def _parse_xbiz_date(fragment):
    # XBIZ cards expose dates as strings such as "Sep 10, 2026".
    matches=re.findall(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\b',fragment)
    if not matches:
        return None
    full=re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\b',fragment)
    if not full:
        return None
    try:
        return datetime.strptime(full.group(0),'%b %d, %Y').replace(tzinfo=timezone.utc)
    except Exception:
        return None


def fetch_xbiz_direct(limit=12):
    """Direct fallback because Google News frequently suppresses adult-trade domains."""
    url='https://www.xbiz.com/news/'
    try:
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; UnderreportedV4/1.0)'})
        raw=urlopen(req,timeout=20).read().decode('utf-8','ignore')
    except Exception as exc:
        print('XBIZ direct fallback failed:',exc)
        return []

    # Find article anchors. Keep the surrounding card text so we can recover the
    # real publication date instead of inventing one.
    found=[];seen=set()
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']*/news/\d+/[^"\']+)["\'][^>]*>(.*?)</a>',raw,re.I|re.S):
        href=html_lib.unescape(m.group(1))
        title=_strip_tags(m.group(2))
        if len(title)<12:
            continue
        lower=title.lower()
        if any(term in lower for term in XBIZ_EXPLICIT_SKIP):
            continue
        if not any(term in lower for term in XBIZ_KEEP_HINTS):
            continue
        link=urljoin(url,href)
        if link in seen:
            continue
        nearby=raw[max(0,m.start()-700):min(len(raw),m.end()+900)]
        published=_parse_xbiz_date(_strip_tags(nearby))
        if published is None:
            continue
        seen.add(link)
        found.append({
            'title':title,
            'link':link,
            'description':f'XBIZ reports an adult-entertainment industry development involving {title}.',
            'pubDate':format_datetime(published),
            'published':published,
            'source':'XBIZ',
            'category':'entertainment',
            'imageUrl':'',
            '_dirty_source':'XBIZ',
        })
        if len(found)>=limit:
            break
    print(f'entertainment dirty/XBIZ direct: {len(found)} accepted')
    return found


def collect():
    items=[]
    forced_dirty=[]
    forced_adult=[]
    query=core.QUERIES.get('entertainment', [])
    combined=' OR '.join(f'({q})' for q in query) if isinstance(query,list) else query
    try:
        batch=core.parse_items(core.fetch(combined),'entertainment')
        items.extend(batch)
        print(f'entertainment primary: {len(batch)} accepted')
    except Exception as exc:
        print('Entertainment primary feed failed:',exc)

    for source,q in PREVIEW_SOURCES:
        try:
            batch=core.parse_items(core.fetch(q),'entertainment',source_override=source)
            items.extend(batch)
            print(f'entertainment preview/{source}: {len(batch)} accepted')
        except Exception as exc:
            print(f'Entertainment preview failed for {source}: {exc}')

    for source,q in DIRTY_PREVIEW_SOURCES:
        try:
            batch=core.parse_items(core.fetch(q),'entertainment',source_override=source)
            items.extend(batch)
            source_key=source.strip().lower()
            for item in batch:
                tagged=dict(item);tagged['_dirty_source']=source
                forced_dirty.append(tagged)
                if source_key in ADULT_TRADE_SOURCES:
                    forced_adult.append(tagged)
            print(f'entertainment dirty/{source}: {len(batch)} accepted')
        except Exception as exc:
            print(f'Entertainment dirty preview failed for {source}: {exc}')

    # If Google News yields no adult-trade stories, pull a restrained subset
    # directly from XBIZ's public news page.
    if not forced_adult:
        direct=fetch_xbiz_direct()
        items.extend(direct)
        forced_dirty.extend(direct)
        forced_adult.extend(direct)

    selected=v4.select_entertainment([x for x in items if x.get('category')=='entertainment'],v4.ENTERTAINMENT_LIMIT)

    existing={_key(x) for x in selected}
    reserve=[]
    for item in _newest_distinct(forced_adult,ADULT_RESERVE):
        k=_key(item)
        if k and k not in existing:
            reserve.append(_decorate_dirty(item,adult_trade=True));existing.add(k)
    for item in _newest_distinct(forced_dirty,DIRTY_RESERVE*2):
        if len(reserve)>=DIRTY_RESERVE:
            break
        k=_key(item)
        if not k or k in existing:
            continue
        adult=(item.get('_dirty_source') or '').strip().lower() in ADULT_TRADE_SOURCES
        reserve.append(_decorate_dirty(item,adult_trade=adult));existing.add(k)

    if reserve:
        keep=max(0,v4.ENTERTAINMENT_LIMIT-len(reserve))
        selected=selected[:keep]+reserve

    forced_map={_key(x):x for x in forced_dirty}
    normalized=[]
    for item in selected:
        k=_key(item)
        src=(item.get('source') or '').strip().lower()
        if k in forced_map:
            adult=src in ADULT_TRADE_SOURCES or (forced_map[k].get('_dirty_source') or '').strip().lower() in ADULT_TRADE_SOURCES
            item=_decorate_dirty(item,adult_trade=adult)
        normalized.append(item)
    selected=normalized

    clean=sum(1 for x in selected if x.get('entertainmentSafety')=='clean')
    dirty=sum(1 for x in selected if x.get('entertainmentSafety')=='dirty')
    adult=sum(1 for x in selected if x.get('entertainmentLabel')=='ADULT INDUSTRY')
    print('Selected Entertainment stories:',len(selected))
    print('  Clean:',clean)
    print('  Dirty-only:',dirty)
    print('  Adult-industry:',adult)
    return selected


def append_node(channel,item):
    n=ET.Element('item')
    def add(tag,val):
        e=ET.SubElement(n,tag);e.text=str(val or '')
    add('title',item.get('title'));add('link',item.get('link'));add('description',item.get('description'))
    add('pubDate',item.get('pubDate'));add('source',item.get('source'));add('category','entertainment')
    add('region','');add('state','');add('imageUrl',item.get('imageUrl',''))
    add('entertainmentTier',item.get('entertainmentTier',''))
    add('entertainmentSafety',item.get('entertainmentSafety','clean'))
    add('entertainmentLabel',item.get('entertainmentLabel','ENTERTAINMENT'))
    add('entertainmentScore',item.get('entertainmentScore',''))
    add('whyMatters','Why it matters: It may affect careers, productions, releases, contracts, audiences, or the wider entertainment industry.')
    channel.append(n)


def main():
    if not NEWS.exists():
        raise SystemExit('News feed not found')
    selected=collect()
    if not selected:
        raise SystemExit('No verified Entertainment stories were collected')
    tree=ET.parse(NEWS);root=tree.getroot();channel=root.find('channel')
    if channel is None: raise SystemExit('RSS channel missing')
    for node in list(channel.findall('item')):
        if (node.findtext('category') or '').strip().lower()=='entertainment':
            channel.remove(node)
    for item in selected:
        append_node(channel,item)
    last=channel.find('lastBuildDate')
    if last is not None:last.text=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Wrote {len(selected)} Entertainment stories to News')

if __name__=='__main__':main()
