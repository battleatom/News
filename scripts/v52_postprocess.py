#!/usr/bin/env python3
from __future__ import annotations
import argparse,re,xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

SKIP={'top','x','underreported','boxoffice'}
GEO={'world','us','nm','local','region'}
SPORT=re.compile(r'\b(football|basketball|baseball|hockey|soccer|volleyball|softball|golf|tennis|sports scoreboard|prep sports|high school sports|college football|ncaa|ncaaf)\b',re.I)
TECH=re.compile(r'\b(ai|artificial intelligence|chatgpt|openai|anthropic|cybersecurity|cyberattack|data breach|semiconductor|nvidia|amd|intel|iphone|ios\s*\d*|android|software|cloud computing|data center|robotics|quantum computing)\b',re.I)
GAMING=re.compile(r'\b(playstation|xbox|nintendo|switch 2|steam|video game|gaming|game pass|pc gamer|esports|dlc|game studio|game developer|epic games|unreal engine|arc raiders|destiny|marathon)\b',re.I)
TABLETOP=re.compile(r'\b(dungeons?\s*&\s*dragons|d&d|tabletop|board game|card game|drinking game|party game)\b',re.I)
FOREIGN=re.compile(r'\b(ukraine|russia|china|iran|israel|gaza|europe|european|germany|france|britain|uk\b|united kingdom|canada|mexico|japan|india|taiwan|nato|united nations|south korea|north korea|saudi|yemen|iraq|syria|afghanistan|foreign minister|prime minister|parliament|diplomat|sanctions)\b',re.I)
US_LOCAL=re.compile(r'\b(indiana|indianapolis|ohio|florida|texas|california|arizona|colorado|utah|new mexico|new york|pennsylvania|georgia|michigan|minnesota|wisconsin|iowa|missouri|kentucky|tennessee|virginia|carolina|alabama|mississippi|arkansas|oklahoma|oregon|washington state|idaho|montana|wyoming|nevada)\b',re.I)
OFFICIAL_LEG=re.compile(r'(congress\.gov|nmlegis\.gov|legis\.state\.nm\.us|new mexico legislature|federal register|\.gov\b)',re.I)
STOP=set('the a an and or but to of in on for with at by from as is are was were be been that this it its they them will would could may after before over under into about new news says report reports latest breaking'.split())

def f(i,n): return (i.findtext(n) or '').strip()
def clean_title(i):
    t=f(i,'title')
    p=t.rsplit(' - ',1)
    if len(p)==2 and 1<=len(p[1].split())<=10:t=p[0]
    return t.strip()
def source_id(i): return re.sub(r'[^a-z0-9]+','',f(i,'source').lower()) or 'unknown'
def setcat(i,c):
    e=i.find('category')
    if e is None:e=ET.SubElement(i,'category')
    e.text=c

def tokens(i):
    s=re.sub(r'[^a-z0-9 ]+',' ',clean_title(i).lower())
    return {x for x in s.split() if len(x)>2 and x not in STOP}
def similarity(a,b):
    A=tokens(a);B=tokens(b)
    if not A or not B:return 0.0
    return len(A&B)/min(len(A),len(B))

def category_guard(i):
    c=f(i,'category').lower();t=clean_title(i);alltxt=' '.join([t,f(i,'description'),f(i,'source'),f(i,'link')])
    if c in {'nm','local','region','world'} and SPORT.search(t): return 'reject','sports-in-civic-tab'
    if c=='world':
        if TECH.search(t) and not re.search(r'\b(law|regulation|government|minister|parliament|ban|policy|summit|treaty)\b',t,re.I): return 'technology','strong-tech-owner'
        if US_LOCAL.search(t) and not FOREIGN.search(alltxt): return 'reject','domestic-local-in-world'
        if re.search(r'\bindiana jones\b',t,re.I): return 'reject','title-entity-false-positive'
    if c in {'local','region','nm','us'} and TECH.search(t) and not re.search(r'\b(government|law|regulation|policy|court|agency)\b',t,re.I): return 'technology','strong-tech-owner'
    if c=='gaming' and TABLETOP.search(t) and not GAMING.search(t): return 'reject','non-video-game-content'
    if c=='technology' and GAMING.search(t) and not TECH.search(t): return 'gaming','strong-gaming-owner'
    if c=='legislation' and not OFFICIAL_LEG.search(alltxt): return 'reject','non-official-legislation-source'
    return 'keep',''

def collapse_same_event(items):
    out=[];removed=[]
    for i in items:
        dup=None
        for kept in out:
            if similarity(i,kept)>=0.88:
                dup=kept;break
        if dup is None:out.append(i)
        else:removed.append((i,dup))
    return out,removed

def rotate(items):
    buckets=defaultdict(list)
    for i in items:buckets[source_id(i)].append(i)
    out=[];r=0
    while True:
        round_items=[]
        for bucket in buckets.values():
            if len(bucket)>r:round_items.append(bucket[r])
        if not round_items:break
        out.extend(round_items);r+=1
    return out

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
    final=[];dups=[]
    for cat,rows in bycat.items():
        collapsed,rm=collapse_same_event(rows);dups.extend((cat,clean_title(a),clean_title(b)) for a,b in rm)
        final.extend(collapsed if cat in SKIP else rotate(collapsed))
    for i in list(channel.findall('item')):channel.remove(i)
    for i in final:channel.append(i)
    ET.indent(tree,space='  ');tree.write(path,encoding='utf-8',xml_declaration=True)
    data={'input':len(items),'output':len(final),'rejected':len(rejected),'rerouted':len(rerouted),'sameEventRemoved':len(dups),'rejectedExamples':rejected[:80],'reroutedExamples':rerouted[:80],'duplicateExamples':dups[:80]}
    if report:report.write_text(__import__('json').dumps(data,indent=2)+'\n',encoding='utf-8')
    print(data)
    return data

def main():
    p=argparse.ArgumentParser();p.add_argument('--feed',default='News');p.add_argument('--report',default='/tmp/v52-postprocess.json');a=p.parse_args();process(Path(a.feed),Path(a.report));return 0
if __name__=='__main__':raise SystemExit(main())
