#!/usr/bin/env python3
"""Collapse repeated coverage into one primary card plus ranked supporting links.

Two passes run before the final verifier:
1. Per-tab consolidation for normal news sections.
2. Cross-tab canonicalization for overlapping civic-news tabs (U.S., Presidential,
   Federal Government) so one real-world event does not occupy multiple cards.

Matching is generic: syndication similarity, exact monetary fingerprints, event
vocabulary, dates, named actors/entities and headline anchors. No person, party,
outlet ideology, or current topic is hard-coded into event identity.
"""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import verify_feed as vf

NEWS=Path('News')
EXCLUDED={'legislation','x','boxoffice'}
OVERLAP_FAMILIES=(frozenset({'us','presidential','federal'}),)
EVENT_WORDS={
 'commemoration':{'anniversary','memorial','remembrance','commemoration','commemorate','tribute','patriot'},
 'payments':{'payment','payments','check','checks','rebate','rebates','dividend','dividends','stimulus','refund','refunds','bonus','payout','cash','promise','promises','promised','pledge','pledges','pledged'},
 'military':{'war','airstrike','missile','strike','troops','invasion','ceasefire','attack','raid'},
 'courts':{'court','judge','ruling','lawsuit','appeal','injunction','supreme'},
 'elections':{'election','midterm','vote','ballot','campaign'},
 'economy':{'tariff','tariffs','trade','economy','market','prices','wages'},
 'disaster':{'hurricane','tornado','wildfire','flood','earthquake','storm','evacuation'},
 'crime':{'shooting','murder','homicide','arrest','charged','indictment','stabbing'},
 'technology':{'cybersecurity','breach','hack','outage','vulnerability','launch'},
 'sports':{'game','match','injury','trade','playoff','championship','score'},
}
STOP=vf.GENERIC|{'coverage','reporting','story','marks','mark','remember','remembering'}

PRIMARY_SOURCE_TIERS={
 'reuters':100,'associated press':100,'ap news':100,
 'bbc':92,'npr':92,
 'cbs news':86,'nbc news':86,'abc news':86,'fox news':86,'cnn':86,
 'the new york times':82,'the washington post':82,'usa today':80,
 'politico':78,'the hill':78,
 'ars technica':82,'the verge':82,'techcrunch':78,
 'nfl.com':82,'espn':82,'ign':78,'gamespot':78,
}
MAX_STRONG_EVENT_SPAN_SECONDS=5*24*60*60

def toks(item):
    return {w for w in re.findall(r'[a-z0-9]+',vf.full_text(item).lower()) if len(w)>=3 and w not in STOP}

def title_toks(item):
    return {w for w in re.findall(r'[a-z0-9]+',vf.title(item).lower()) if len(w)>=3 and w not in STOP}

def entertainment_title_toks(item):
    """Lightly normalize headline words for same-event Entertainment coverage.

    Entertainment outlets often describe one announcement with different grammar
    (for example reunion/reunions or presenter/presenters).  Singularizing only
    longer headline tokens improves event identity without using a topic-specific
    person, show, award, or outlet rule.
    """
    out=set()
    for word in title_toks(item):
        if len(word)>4 and word.endswith('ies'):
            word=word[:-3]+'y'
        elif len(word)>4 and word.endswith('s') and not word.endswith('ss'):
            word=word[:-1]
        out.add(word)
    return out

def entertainment_event_match(a,b):
    if vf.category(a)!='entertainment' or vf.category(b)!='entertainment': return False
    if not near_in_time(a,b): return False
    ta,tb=entertainment_title_toks(a),entertainment_title_toks(b)
    if not ta or not tb: return False
    shared=ta&tb;smaller=min(len(ta),len(tb))
    entities=vf.entity_keys(a)&vf.entity_keys(b)
    # Four normalized headline anchors with strong proportional overlap identify
    # the same announcement even when the titles are independently rewritten.
    if len(shared)>=4 and len(shared)/max(1,smaller)>=0.55: return True
    # Named-entity agreement allows slightly shorter rewritten headlines, but still
    # requires three concrete shared headline anchors to avoid broad celebrity merges.
    if entities and len(shared)>=3 and len(shared)/max(1,smaller)>=0.60: return True
    return False

def groups(item):
    t=toks(item)|title_toks(item)
    return {k for k,v in EVENT_WORDS.items() if t&v}|vf.event_groups(item)

def slash_date_keys(item):
    text=vf.full_text(item).lower();out=set()
    for m,d in re.findall(r'\b(\d{1,2})/(\d{1,2})\b',text):
        mi,di=int(m),int(d)
        if 1<=mi<=12 and 1<=di<=31: out.add(f'date:{mi}/{di}')
    for month,day in re.findall(r'\b(september|october|november|december|january|february|march|april|may|june|july|august)\s+(\d{1,2})\b',text):
        out.add(f'date:{month}:{int(day)}')
    return out

def usd_keys(item):
    return {k for k in vf.amount_keys(item) if k.startswith('usd:')}

def near_in_time(a,b):
    ta,tb=vf.parsed_time(a),vf.parsed_time(b)
    return not ta or not tb or abs(ta-tb)<=MAX_STRONG_EVENT_SPAN_SECONDS

def same_event(a,b):
    if vf.category(a)!=vf.category(b): return False
    return event_match(a,b,allow_cross_tab=False)

def in_same_overlap_family(a,b):
    ca,cb=vf.category(a),vf.category(b)
    return any(ca in fam and cb in fam for fam in OVERLAP_FAMILIES)

def event_match(a,b,allow_cross_tab=False):
    if not allow_cross_tab and vf.category(a)!=vf.category(b): return False
    if allow_cross_tab and not in_same_overlap_family(a,b): return False
    if vf.syndicated_copy(a,b): return True
    if not allow_cross_tab and vf.same_event(a,b): return True
    if not allow_cross_tab and entertainment_event_match(a,b): return True

    ga,gb=groups(a),groups(b);shared_groups=ga&gb
    shared=toks(a)&toks(b);tshared=title_toks(a)&title_toks(b)
    entities=vf.entity_keys(a)&vf.entity_keys(b)
    actors=vf.actor_keys(a)&vf.actor_keys(b)
    usd_a,usd_b=usd_keys(a),usd_keys(b)
    exact_usd=usd_a&usd_b
    generic_numbers=(vf.amount_keys(a)&vf.amount_keys(b))-exact_usd
    dates=slash_date_keys(a)&slash_date_keys(b)
    conflicting_usd=bool(usd_a and usd_b and not exact_usd)
    if exact_usd and (actors or entities) and near_in_time(a,b): return True
    if exact_usd and shared_groups and len(shared)>=2 and near_in_time(a,b): return True
    if conflicting_usd: return False
    if generic_numbers and shared_groups and (actors or entities) and len(tshared)>=2 and len(shared)>=4 and near_in_time(a,b): return True
    if dates and shared_groups and (actors or entities) and len(shared)>=2: return True
    if shared_groups and entities and len(tshared)>=3 and len(shared)>=4: return True
    if shared_groups and actors and len(tshared)>=3 and len(shared)>=4: return True
    if shared_groups and len(tshared)>=5 and len(shared)>=5: return True
    return False

def source_tier(item):
    source=(item.findtext('source') or '').strip().lower()
    return max((score for key,score in PRIMARY_SOURCE_TIERS.items() if key in source),default=60)

def primary_score(item):
    return (source_tier(item),)+vf.representative_score(item)[1:]

def canonical_category(cluster):
    cats={vf.category(x) for x in cluster}
    return max(cats,key=lambda c:(vf.SPECIFICITY.get(c,0),c))

def set_category(item,value):
    node=item.find('category')
    if node is None: node=ET.SubElement(item,'category')
    node.text=value

def related_key(node):
    return ((node.findtext('link') or '').strip() or (node.findtext('title') or '').strip()).lower()

def append_related_node(primary,node):
    rel=primary.find('relatedArticles')
    if rel is None: rel=ET.SubElement(primary,'relatedArticles')
    existing={related_key(x) for x in rel.findall('article')};k=related_key(node)
    if not k or k in existing: return 0
    ar=ET.SubElement(rel,'article')
    for tag in ('title','link','source','pubDate'):
        value=(node.findtext(tag) or '').strip()
        if value: ET.SubElement(ar,tag).text=value
    return 1

def attach(primary,other):
    added=append_related_node(primary,other)
    for nested in other.findall('./relatedArticles/article'):
        added+=append_related_node(primary,nested)
    return added

def component_clusters(rows,matcher):
    if not rows: return []
    parent=list(range(len(rows)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[rb]=ra
    for i,a in enumerate(rows):
        for j in range(i+1,len(rows)):
            if matcher(a,rows[j]): union(i,j)
    out=defaultdict(list)
    for i,row in enumerate(rows): out[find(i)].append(row)
    return list(out.values())

def collapse_cluster(cluster,removed,force_canonical=False):
    cluster=[x for x in cluster if id(x) not in removed]
    if len(cluster)<2: return (0,0)
    primary=max(cluster,key=primary_score)
    if force_canonical: set_category(primary,canonical_category(cluster))
    added=0
    for other in sorted((x for x in cluster if x is not primary),key=primary_score,reverse=True):
        added+=attach(primary,other);removed.add(id(other))
    return (1,added)

def consolidate_rows(rows,removed):
    clusters=attached=0
    for cluster in component_clusters([x for x in rows if id(x) not in removed],same_event):
        c,a=collapse_cluster(cluster,removed);clusters+=c;attached+=a
    return clusters,attached

def consolidate_cross_tab(items,removed):
    clusters=attached=0
    for family in OVERLAP_FAMILIES:
        rows=[x for x in items if vf.category(x) in family and id(x) not in removed]
        for cluster in component_clusters(rows,lambda a,b:event_match(a,b,allow_cross_tab=True)):
            if len({vf.category(x) for x in cluster})<2: continue
            c,a=collapse_cluster(cluster,removed,force_canonical=True);clusters+=c;attached+=a
    return clusters,attached

def main():
    tree=ET.parse(NEWS);channel=tree.getroot().find('channel')
    items=list(channel.findall('item'));bycat=defaultdict(list)
    for item in items:
        cat=vf.category(item)
        if cat not in EXCLUDED: bycat[cat].append(item)
    removed=set();clusters=attached=0
    for rows in bycat.values():
        c,a=consolidate_rows(rows,removed);clusters+=c;attached+=a
    cross_c,cross_a=consolidate_cross_tab(items,removed)
    clusters+=cross_c;attached+=cross_a
    if removed:
        for item in list(channel.findall('item')):
            if id(item) in removed: channel.remove(item)
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Related coverage clustering: {clusters} event cluster(s), {attached} supporting link(s) retained; {cross_c} cross-tab cluster(s).')

if __name__=='__main__': main()
