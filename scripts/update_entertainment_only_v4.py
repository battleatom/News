#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import update_news_v4 as v4

core=v4.core
NEWS=Path('News')

# Preview deliberately samples both professional and broad-entertainment outlets so
# the Clean/Dirty toggle always has a meaningful live pool to exercise.
PREVIEW_SOURCES=[
    ('People','site:people.com celebrity actor actress dating relationship baby wedding fashion charity'),
    ('TMZ','site:tmz.com celebrity actor actress dating fashion adult film star'),
    ('E! News','site:eonline.com celebrity actor actress dating relationship fashion red carpet'),
    ('Variety','site:variety.com actor actress Hollywood television film entertainment'),
    ('Billboard','site:billboard.com music artist singer rapper tour album'),
    ('Deadline','site:deadline.com actor actress television film Hollywood'),
]

def collect():
    items=[]
    query=core.QUERIES.get('entertainment', [])
    combined=' OR '.join(f'({q})' for q in query) if isinstance(query,list) else query
    try:
        batch=core.parse_items(core.fetch(combined),'entertainment')
        items.extend(batch)
        print(f'entertainment primary: {len(batch)} accepted')
    except Exception as exc:
        print('Entertainment primary feed failed:',exc)

    # Always sample each preview source instead of stopping as soon as one outlet
    # fills the numeric quota. Source diversity is part of the feature being tested.
    for source,q in PREVIEW_SOURCES:
        try:
            batch=core.parse_items(core.fetch(q),'entertainment',source_override=source)
            items.extend(batch)
            print(f'entertainment preview/{source}: {len(batch)} accepted')
        except Exception as exc:
            print(f'Entertainment preview failed for {source}: {exc}')

    selected=v4.select_entertainment([x for x in items if x.get('category')=='entertainment'],v4.ENTERTAINMENT_LIMIT)
    clean=sum(1 for x in selected if x.get('entertainmentSafety')=='clean')
    dirty=sum(1 for x in selected if x.get('entertainmentSafety')=='dirty')
    print('Selected Entertainment stories:',len(selected))
    print('  Clean:',clean)
    print('  Dirty-only:',dirty)
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
