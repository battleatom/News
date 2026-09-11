#!/usr/bin/env python3
"""Collapse repeated same-event cards into one primary card with supporting links.

This runs before the final verifier. It is category-agnostic for normal news tabs:
no topic-specific blocklist is used. Event matching combines the verifier's strict
matcher with conservative fingerprints for named entities, event vocabulary,
amounts/dates and headline anchors. Official legislation is intentionally excluded.
"""
from __future__ import annotations
import copy
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import verify_feed as vf

NEWS=Path('News')
EXCLUDED={'legislation','x','boxoffice'}
EVENT_WORDS={
 'commemoration':{'anniversary','memorial','remembrance','commemoration','commemorate','tribute','patriot'},
 'payments':{'payment','payments','check','checks','rebate','rebates','dividend','dividends','stimulus','refund','refunds','bonus','payout','cash'},
 'military':{'war','airstrike','missile','strike','troops','invasion','ceasefire','attack','raid'},
 'courts':{'court','judge','ruling','lawsuit','appeal','injunction','supreme'},
 'elections':{'election','midterm','vote','ballot','campaign'},
 'disaster':{'hurricane','tornado','wildfire','flood','earthquake','storm','evacuation'},
 'crime':{'shooting','murder','homicide','arrest','charged','indictment','stabbing'},
 'technology':{'cybersecurity','breach','hack','outage','vulnerability','launch'},
 'sports':{'game','match','injury','trade','playoff','championship','score'},
}
STOP=vf.GENERIC|{'coverage','reporting','story','marks','mark','remember','remembering'}

def toks(item):
    return {w for w in re.findall(r'[a-z0-9]+',vf.full_text(item).lower()) if len(w)>=3 and w not in STOP}

def title_toks(item):
    return {w for w in re.findall(r'[a-z0-9]+',vf.title(item).lower()) if len(w)>=3 and w not in STOP}

def groups(item):
    t=toks(item)|title_toks(item)
    return {k for k,v in EVENT_WORDS.items() if t&v}|vf.event_groups(item)

def slash_date_keys(item):
    text=vf.full_text(item).lower()
    out=set()
    for m,d in re.findall(r'\b(\d{1,2})/(\d{1,2})\b',text):
        mi,di=int(m),int(d)
        if 1<=mi<=12 and 1<=di<=31: out.add(f'date:{mi}/{di}')
    for month,day in re.findall(r'\b(september|october|november|december|january|february|march|april|may|june|july|august)\s+(\d{1,2})\b',text):
        out.add(f'date:{month}:{int(day)}')
    return out

def same_event(a,b):
    if vf.category(a)!=vf.category(b): return False
    if vf.same_event(a,b): return True
    ga,gb=groups(a),groups(b)
    if not ga&gb: return False
    shared=toks(a)&toks(b); tshared=title_toks(a)&title_toks(b)
    entities=vf.entity_keys(a)&vf.entity_keys(b)
    numbers=vf.amount_keys(a)&vf.amount_keys(b)
    dates=slash_date_keys(a)&slash_date_keys(b)
    # Strong event fingerprints. A broad person/subject by itself never clusters.
    if numbers and len(shared)>=2: return True
    if dates and len(shared)>=2: return True
    if entities and len(tshared)>=2 and len(shared)>=3: return True
    if len(tshared)>=4 and len(shared)>=4: return True
    return False

def related_key(node):
    return ((node.findtext('link') or '').strip() or (node.findtext('title') or '').strip()).lower()

def attach(primary,other):
    rel=primary.find('relatedArticles')
    if rel is None: rel=ET.SubElement(primary,'relatedArticles')
    existing={related_key(x) for x in rel.findall('article')}
    k=related_key(other)
    if not k or k in existing: return
    ar=ET.SubElement(rel,'article')
    for tag in ('title','link','source','pubDate'):
        value=(other.findtext(tag) or '').strip()
        if value: ET.SubElement(ar,tag).text=value

def main():
    tree=ET.parse(NEWS); channel=tree.getroot().find('channel')
    items=list(channel.findall('item')); bycat=defaultdict(list)
    for item in items:
        cat=vf.category(item)
        if cat not in EXCLUDED: bycat[cat].append(item)
    removed=set(); clusters=0; attached=0
    for cat,rows in bycat.items():
        used=set()
        for i,a in enumerate(rows):
            if i in used: continue
            cluster=[a]
            for j in range(i+1,len(rows)):
                if j in used: continue
                if any(same_event(member,rows[j]) for member in cluster[:4]):
                    cluster.append(rows[j]); used.add(j)
            if len(cluster)<2: continue
            primary=max(cluster,key=vf.representative_score); clusters+=1
            for other in cluster:
                if other is primary: continue
                attach(primary,other); attached+=1; removed.add(id(other))
    if removed:
        for item in list(channel.findall('item')):
            if id(item) in removed: channel.remove(item)
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Related coverage clustering: {clusters} event cluster(s), {attached} duplicate card(s) moved to supporting links.')

if __name__=='__main__': main()
