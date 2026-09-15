#!/usr/bin/env python3
from __future__ import annotations
import argparse,heapq,re,xml.etree.ElementTree as ET
from collections import defaultdict,deque
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit

SKIP_SEQUENCE={'top','x','underreported','boxoffice'}
GEO={'world','us','nm','local','region'}
SPORT=re.compile(r'\b(nfl|nba|mlb|nhl|football|basketball|baseball|hockey|soccer|volleyball|softball|golf|tennis|sports scoreboard|prep sports|high school sports|college football|ncaa|ncaaf|quarterback|touchdown)\b',re.I)
SPORT_SOURCE=re.compile(r'\b(espn|yahoo sports|sports illustrated|cbs sports|fox sports|nbc sports|the athletic)\b',re.I)
OBIT=re.compile(r'\b(obituary|obituaries)\b',re.I)
TECH=re.compile(r'\b(ai|artificial intelligence|chatgpt|openai|anthropic|cyber(?:security|attack)?|ransomware|malware|data breach|semiconductor|nvidia|amd|intel|iphone|ios\s*\d*|android|software|cloud computing|data centers?|robotics|quantum computing|firewall|hacker|hacking)\b',re.I)
TECH_SOURCE=re.compile(r'\b(ars technica|techcrunch|wired|the verge|tech times|tom.s hardware|industrial cyber|hpcwire|channel insider)\b',re.I)
GAMING=re.compile(r'\b(playstation|xbox|nintendo|switch 2|steam|video game|gaming|game pass|pc gamer|esports|dlc|game studio|game developer|epic games|unreal engine|arc raiders|destiny|marathon)\b',re.I)
TABLETOP=re.compile(r'\b(dungeons?\s*&\s*dragons|d&d|tabletop|board game|card game|drinking game|party game)\b',re.I)
FOREIGN=re.compile(r'\b(ukraine|russia|china|iran|israel|gaza|europe|european|germany|france|britain|uk\b|united kingdom|canada|mexico|japan|india|taiwan|nato|united nations|south korea|north korea|saudi|yemen|iraq|syria|afghanistan|foreign minister|prime minister|parliament|diplomat|sanctions)\b',re.I)
US_LOCAL=re.compile(r'\b(indiana|indianapolis|ohio|florida|texas|california|arizona|colorado|utah|new mexico|new york|pennsylvania|georgia|michigan|minnesota|wisconsin|iowa|missouri|kentucky|tennessee|virginia|carolina|alabama|mississippi|arkansas|oklahoma|oregon|washington state|idaho|montana|wyoming|nevada)\b',re.I)
OFFICIAL_LEG=re.compile(r'(congress\.gov|nmlegis\.gov|legis\.state\.nm\.us|new mexico legislature|federal register|\.gov\b)',re.I)
STOP=set('the a an and or but to of in on for with at by from as is are was were be been that this it its they them will would could may after before over under into about new news says report reports latest breaking'.split())

def f(i,n):return (i.findtext(n) or '').strip()
def clean_title(i):
    t=f(i,'title');p=t.rsplit(' - ',1)
    if len(p)==2 and 1<=len(p[1].split())<=10:t=p[0]
    return t.strip()
def canon_title(i):return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]+',' ',clean_title(i).lower())).strip()
def canon_url(i):
    try:
        p=urlsplit(f(i,'link'));return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),'',''))
    except Exception:return f(i,'link').lower()
def source_id(i):
    s=f(i,'source').lower().strip();s=re.sub(r'^the\s+','',s);s=re.sub(r'\.(com|org|net)$','',s)
    return re.sub(r'[^a-z0-9]+','',s) or 'unknown'
def setcat(i,c):
    e=i.find('category')
    if e is None:e=ET.SubElement(i,'category')
    e.text=c

def tokens(i):
    s=re.sub(r'[^a-z0-9 ]+',' ',clean_title(i).lower())
    return {x for x in s.split() if len(x)>2 and x not in STOP}
def similarity(a,b):
    A=tokens(a);B=tokens(b)
    if min(len(A),len(B))<5 or len(A&B)<4:return 0.0
    return len(A&B)/min(len(A),len(B))

def category_guard(i):
    c=f(i,'category').lower();t=clean_title(i);src=f(i,'source');alltxt=' '.join([t,f(i,'description'),src,f(i,'link')])
    if c in {'nm','local','region','world'} and (SPORT.search(t) or SPORT_SOURCE.search(src)):return 'reject','sports-in-civic-tab'
    if c in {'nm','local','region'} and OBIT.search(t):return 'reject','obituary-in-news-bank'
    if c=='world':
        if (TECH.search(t) or TECH_SOURCE.search(src)) and not re.search(r'\b(law|regulation|government|minister|parliament|ban|policy|summit|treaty)\b',t,re.I):return 'technology','strong-tech-owner'
        if US_LOCAL.search(t) and not FOREIGN.search(alltxt):return 'reject','domestic-local-in-world'
        if re.search(r'\bindiana jones\b',t,re.I):return 'reject','title-entity-false-positive'
    if c in {'local','region','nm','us'} and (TECH.search(t) or TECH_SOURCE.search(src)) and not re.search(r'\b(government|law|regulation|policy|court|agency)\b',t,re.I):return 'technology','strong-tech-owner'
    if c=='us' and FOREIGN.search(t) and re.search(r'\b(houthi|yemen|ukraine|russia|iran|gaza|israel)\b',t,re.I) and not re.search(r'\b(congress|white house|federal|u\.s\.|us\s)',t,re.I):return 'world','strong-foreign-owner'
    if c=='gaming' and TABLETOP.search(t) and not GAMING.search(t):return 'reject','non-video-game-content'
    if c=='technology' and GAMING.search(t) and not TECH.search(t):return 'gaming','strong-gaming-owner'
    if c=='legislation' and not OFFICIAL_LEG.search(alltxt):return 'reject','non-official-legislation-source'
    return 'keep',''

def collapse_same_event(items):
    out=[];removed=[];seen_title={};seen_url={}
    for i in items:
        ct=canon_title(i);cu=canon_url(i);dup=None
        if ct and ct in seen_title:dup=seen_title[ct]
        elif cu and cu in seen_url:dup=seen_url[cu]
        else:
            for kept in out:
                if similarity(i,kept)>=0.82:dup=kept;break
        if dup is None:
            out.append(i)
            if ct:seen_title[ct]=i
            if cu:seen_url[cu]=i
        else:removed.append((i,dup))
    return out,removed

def balanced_schedule(items,max_streak=2):
    """Preserve all feasible stories while preventing publisher blocks.

    Sources with the most remaining stories are placed early enough that they do not
    become an unavoidable tail. If a pool is mathematically impossible to schedule
    at max_streak (for example one publisher owns almost the entire pool), only the
    unavoidable excess tail is dropped rather than showing a long publisher block.
    """
    buckets=defaultdict(deque);first={}
    for idx,i in enumerate(items):
        sid=source_id(i);buckets[sid].append(i);first.setdefault(sid,idx)
    heap=[(-len(q),first[sid],sid) for sid,q in buckets.items() if q];heapq.heapify(heap)
    out=[];last=None;streak=0;dropped=[]
    while heap:
        n,order,sid=heapq.heappop(heap)
        blocked=(sid==last and streak>=max_streak)
        if blocked:
            if not heap:
                dropped.extend(list(buckets[sid]));break
            n2,o2,sid2=heapq.heappop(heap)
            heapq.heappush(heap,(n,order,sid))
            n,order,sid=n2,o2,sid2
        item=buckets[sid].popleft();out.append(item)
        if sid==last:streak+=1
        else:last=sid;streak=1
        if buckets[sid]:heapq.heappush(heap,(-len(buckets[sid]),order,sid))
    return out,dropped

def process(path:Path,report:Path|None=None):
    tree=ET.parse(path);channel=tree.getroot().find('channel');items=list(channel.findall('item'))
    kept=[];rejected=[];rerouted=[]
    for i in items:
        action,reason=category_guard(i);old=f(i,'category').lower()
        if action=='reject':rejected.append((old,clean_title(i),reason));continue
        if action not in {'keep','reject'}:
            setcat(i,action);rerouted.append((old,action,clean_title(i),reason))
        kept.append(i)
    bycat=defaultdict(list)
    for i in kept:bycat[f(i,'category').lower()].append(i)
    final=[];dups=[];tail_drops=[]
    for cat,rows in bycat.items():
        if cat in SKIP_SEQUENCE:
            collapsed,rm=rows,[]
        else:
            collapsed,rm=collapse_same_event(rows)
        dups.extend((cat,clean_title(a),clean_title(b)) for a,b in rm)
        if cat in SKIP_SEQUENCE:
            scheduled=collapsed
        else:
            scheduled,dropped=balanced_schedule(collapsed,2)
            tail_drops.extend((cat,f(x,'source'),clean_title(x)) for x in dropped)
        final.extend(scheduled)
    for i in list(channel.findall('item')):channel.remove(i)
    for i in final:channel.append(i)
    ET.indent(tree,space='  ');tree.write(path,encoding='utf-8',xml_declaration=True)
    data={'input':len(items),'output':len(final),'rejected':len(rejected),'rerouted':len(rerouted),'sameEventRemoved':len(dups),'sourceTailDropped':len(tail_drops),'rejectedExamples':rejected[:100],'reroutedExamples':rerouted[:100],'duplicateExamples':dups[:100],'sourceTailDropExamples':tail_drops[:100]}
    if report:report.write_text(__import__('json').dumps(data,indent=2)+'\n',encoding='utf-8')
    print(data);return data

def main():
    p=argparse.ArgumentParser();p.add_argument('--feed',default='News');p.add_argument('--report',default='/tmp/v52-postprocess.json');a=p.parse_args();process(Path(a.feed),Path(a.report));return 0
if __name__=='__main__':raise SystemExit(main())
