#!/usr/bin/env python3
"""Collapse repeated coverage into one primary card plus supporting links.

Two passes run before the final verifier:
1. Per-tab consolidation for normal news sections.
2. Cross-tab canonicalization for overlapping civic-news tabs (U.S., Presidential,
   Federal Government) so one real-world event does not occupy multiple cards.

Matching is generic: syndication similarity, event vocabulary, amounts/dates,
named actors/entities and headline anchors. No person, party, outlet ideology, or
single current topic is hard-coded into event identity.
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
 'payments':{'payment','payments','check','checks','rebate','rebates','dividend','dividends','stimulus','refund','refunds','bonus','payout','cash'},
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

# Neutral primary-source preference: wire services first, then established national
# straight-news organizations. Cable/network outlets are intentionally not ordered
# by political viewpoint. Recency/completeness break ties.
PRIMARY_SOURCE_TIERS={
 'reuters':100,'associated press':100,'ap news':100,
 'bbc':92,'npr':92,
 'cbs news':86,'nbc news':86,'abc news':86,'fox news':86,'cnn':86,
 'the new york times':82,'the washington post':82,'usa today':80,
 'politico':78,'the hill':78,
 'ars technica':82,'the verge':82,'techcrunch':78,
 'nfl.com':82,'espn':82,'ign':78,'gamespot':78,
}

def toks(item):
    return {w for w in re.findall(r'[a-z0-9]+',vf.full_text(item).lower()) if len(w)>=3 and w not in STOP}

def title_toks(item):
    return {w for w in re.findall(r'[a-z0-9]+',vf.title(item).lower()) if len(w)>=3 and w not in STOP}

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

    ga,gb=groups(a),groups(b)
    shared_groups=ga&gb
    shared=toks(a)&toks(b);tshared=title_toks(a)&title_toks(b)
    entities=vf.entity_keys(a)&vf.entity_keys(b)
    actors=vf.actor_keys(a)&vf.actor_keys(b)
    numbers=vf.amount_keys(a)&vf.amount_keys(b)
    dates=slash_date_keys(a)&slash_date_keys(b)

    # Amount + event type + actor/entity is a durable event identity. This is what
    # combines multiple reports about one payment/proposal while preventing an
    # unrelated story about the same public figure from bridging into the cluster.
    if numbers and shared_groups and (actors or entities): return True
    if numbers and shared_groups and len(shared)>=2: return True

    # Date/entity fingerprints are useful for ceremonies, disasters and scheduled events.
    if dates and shared_groups and (actors or entities) and len(shared)>=2: return True

    # Without an amount/date, require substantially more lexical agreement.
    if shared_groups and entities and len(tshared)>=3 and len(shared)>=4: return True
    if shared_groups and actors and len(tshared)>=3 and len(shared)>=4: return True
    if shared_groups and len(tshared)>=5 and len(shared)>=5: return True
    return False

def source_tier(item):
    source=(item.findtext('source') or '').strip().lower()
    return max((score for key,score in PRIMARY_SOURCE_TIERS.items() if key in source),default=60)

def primary_score(item):
    # Authority/original-reporting proxy first; then verifier recency/completeness score.
    return (source_tier(item),)+vf.representative_score(item)[1:]

def canonical_category(cluster):
    cats={vf.category(x) for x in cluster}
    # For overlapping civic tabs, keep the event on the most specific applicable tab.
    # The classifier's specificity table is structural, not political preference.
    return max(cats,key=lambda c:(vf.SPECIFICITY.get(c,0),c))

def set_category(item,value):
    node=item.find('category')
    if node is None: node=ET.SubElement(item,'category')
    node.text=value

def related_key(node):
    return ((node.findtext('link') or '').strip() or (node.findtext('title') or '').strip()).lower()

def attach(primary,other):
    rel=primary.find('relatedArticles')
    if rel is None: rel=ET.SubElement(primary,'relatedArticles')
    existing={related_key(x) for x in rel.findall('article')};k=related_key(other)
    if not k or k in existing: return False
    ar=ET.SubElement(rel,'article')
    for tag in ('title','link','source','pubDate'):
        value=(other.findtext(tag) or '').strip()
        if value: ET.SubElement(ar,tag).text=value
    return True

def consolidate_rows(rows,matcher,removed):
    clusters=attached=0;used=set()
    for i,a in enumerate(rows):
        if i in used or id(a) in removed: continue
        cluster=[a]
        for j in range(i+1,len(rows)):
            if j in used or id(rows[j]) in removed: continue
            # Star clustering prevents transitive "bridge" stories from joining merely
            # because they resemble a secondary member. Every member must match anchor.
            if matcher(a,rows[j]):
                cluster.append(rows[j]);used.add(j)
        if len(cluster)<2: continue
        primary=max(cluster,key=primary_score);clusters+=1
        for other in sorted((x for x in cluster if x is not primary),key=primary_score,reverse=True):
            if attach(primary,other): attached+=1
            removed.add(id(other))
    return clusters,attached

def consolidate_cross_tab(items,removed):
    clusters=attached=0
    for family in OVERLAP_FAMILIES:
        rows=[x for x in items if vf.category(x) in family and id(x) not in removed]
        used=set()
        for i,a in enumerate(rows):
            if i in used or id(a) in removed: continue
            cluster=[a]
            for j in range(i+1,len(rows)):
                if j in used or id(rows[j]) in removed: continue
                if event_match(a,rows[j],allow_cross_tab=True):
                    cluster.append(rows[j]);used.add(j)
            if len(cluster)<2: continue
            primary=max(cluster,key=primary_score)
            set_category(primary,canonical_category(cluster))
            clusters+=1
            for other in sorted((x for x in cluster if x is not primary),key=primary_score,reverse=True):
                if attach(primary,other): attached+=1
                removed.add(id(other))
    return clusters,attached

def main():
    tree=ET.parse(NEWS);channel=tree.getroot().find('channel')
    items=list(channel.findall('item'));bycat=defaultdict(list)
    for item in items:
        cat=vf.category(item)
        if cat not in EXCLUDED: bycat[cat].append(item)

    removed=set();clusters=attached=0
    for rows in bycat.values():
        c,a=consolidate_rows(rows,same_event,removed);clusters+=c;attached+=a

    cross_c,cross_a=consolidate_cross_tab(items,removed)
    clusters+=cross_c;attached+=cross_a

    if removed:
        for item in list(channel.findall('item')):
            if id(item) in removed: channel.remove(item)
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Related coverage clustering: {clusters} event cluster(s), {attached} duplicate card(s) moved to supporting links; {cross_c} cross-tab cluster(s).')

if __name__=='__main__': main()
