#!/usr/bin/env python3
"""V5.2-only final content guard.

Runs after the existing V5.1 refinement/routing chain. It removes or reroutes
only high-confidence category leaks, preserves the nationwide Local/Region banks
needed for location-relative UX, deduplicates exact official Legislation cards,
and rebalances publishers without discarding valid reporting.
"""
from __future__ import annotations
import heapq,json,re
import xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path

NEWS=Path('News')
REPORT=Path('/tmp/v52-content-guard.json')
ROTATE={'underreported','entertainment','world','us','presidential','federal','nm','local','region','nfl','technology','gaming','military'}
SPORT=re.compile(r'\b(nfl|nba|mlb|nhl|college football|high school football|football|basketball|baseball|hockey|soccer|golf|tennis|touchdown|quarterback|playoff|standings|scouting report|titans|cowboys|broncos|chiefs|raiders|chargers|rams|49ers|seahawks|cardinals|packers|bears|lions|vikings|eagles|giants|jets|commanders|ravens|steelers|browns|bengals|bills|patriots|dolphins|jaguars|texans|colts|falcons|panthers|saints|buccaneers)\b',re.I)
GAMING=re.compile(r'\b(video game|gaming|playstation|ps5|xbox|nintendo|switch 2|steam|game pass|esports|gameplay|dlc|game studio|game developer|pc gamer)\b',re.I)
TECH=re.compile(r'\b(ai|artificial intelligence|openai|chatgpt|anthropic|cybersecurity|ransomware|malware|software|hardware|semiconductor|nvidia|amd|intel|iphone|ios|android|smartphone|laptop|gpu|cpu|data center|robotics?)\b',re.I)
WORLD=re.compile(r'\b(ukraine|russia|china|iran|israel|gaza|france|germany|united kingdom|britain|japan|india|canada|mexico|afghanistan|saudi|taiwan|nato|united nations|europe|africa|asia|middle east|international|foreign minister|prime minister)\b',re.I)
US_LOCAL=re.compile(r'\b(indiana|indianapolis|whiting,? indiana|iowa|west virginia)\b',re.I)
NM=re.compile(r'\b(new mexico|albuquerque|santa fe|las cruces|rio rancho|nmdot)\b',re.I)
TABLETOP=re.compile(r'\b(tabletop|board game|drinking game|party game|d&d-themed|dungeons?\s*&\s*dragons)\b',re.I)
FEDERAL=re.compile(r'\b(congress|house passes|senate|supreme court|scotus|federal court|federal judge|fbi|doj|dhs|irs|epa|treasury|federal government|government shutdown|funding stopgap)\b',re.I)


def field(i,n): return (i.findtext(n) or '').strip()
def sid(i): return re.sub(r'[^a-z0-9]+','',(field(i,'source') or '').lower()) or 'unknown'
def headline(i):
    t=field(i,'title')
    return t.rsplit(' - ',1)[0] if ' - ' in t else t

def set_category(i,cat):
    node=i.find('category')
    if node is None: node=ET.SubElement(i,'category')
    node.text=cat

def norm_title(i):
    return re.sub(r'[^a-z0-9]+',' ',headline(i).lower()).strip()


def decision(i,cat):
    """Return (action, target/reason). Actions: keep, reject, reroute."""
    t=headline(i)
    if cat in {'world','us','presidential','federal','nm','local','region'} and GAMING.search(t):
        return ('reroute','gaming')
    if cat in {'world','us','presidential','federal','nm','local','region'} and SPORT.search(t):
        return ('reject','sports-leak')
    if cat=='world':
        if US_LOCAL.search(t) and not WORLD.search(t): return ('reject','us-local-leak')
        if FEDERAL.search(t) and not WORLD.search(t): return ('reroute','federal')
        if TECH.search(t): return ('reroute','technology')
    if cat=='nm' and not (NM.search(t) or field(i,'state').lower()=='new mexico'):
        if not field(i,'state'): return ('reject','no-new-mexico-anchor')
    # Region is a nationwide inventory bank filtered relative to the viewer in the
    # browser. Never collapse it to one geographic region here; only remove obvious
    # subject leakage. Local works the same way for its market bank.
    if cat=='gaming' and TABLETOP.search(t) and not GAMING.search(t): return ('reject','non-video-game')
    return ('keep','')


def max_streak(rows):
    best=0; last=None; run=0
    for item in rows:
        s=sid(item)
        run=run+1 if s==last else 1
        last=s; best=max(best,run)
    return best


def optimal_streak_bound(rows):
    counts=Counter(sid(x) for x in rows)
    if not counts:return 0
    largest=max(counts.values()); others=sum(counts.values())-largest
    if others==0:return largest
    return max(1,(largest+others)//(others+1) if largest%(others+1)==0 else largest//(others+1)+1)


def balance(rows):
    """Spread dominant publishers while preserving each source's story order."""
    if len(rows)<2:return rows
    buckets=defaultdict(list); first={}
    for pos,item in enumerate(rows):
        s=sid(item);buckets[s].append(item);first.setdefault(s,pos)
    if len(buckets)<2:return rows
    bound=optimal_streak_bound(rows)
    heap=[(-len(bucket),first[s],s) for s,bucket in buckets.items()]
    heapq.heapify(heap)
    out=[];last=None;run=0
    while heap:
        best=heapq.heappop(heap);pick=best
        if best[2]==last and run>=bound and heap:
            pick=heapq.heappop(heap);heapq.heappush(heap,best)
        s=pick[2];out.append(buckets[s].pop(0))
        run=run+1 if s==last else 1;last=s
        if buckets[s]:heapq.heappush(heap,(-len(buckets[s]),first[s],s))
    return out


def grouped_balance(rows,key_name):
    """Balance inside each viewer-selectable Local/Region inventory group."""
    groups=defaultdict(list);order=[]
    for item in rows:
        key=field(item,key_name) or '__unknown__'
        if key not in groups:order.append(key)
        groups[key].append(item)
    out=[]
    for key in order:out.extend(balance(groups[key]))
    return out


def balance_category(cat,rows):
    if cat=='local':return grouped_balance(rows,'marketId')
    if cat=='region':return grouped_balance(rows,'region')
    return balance(rows)


def main():
    tree=ET.parse(NEWS);channel=tree.getroot().find('channel')
    if channel is None:raise SystemExit('RSS channel missing')
    items=list(channel.findall('item'));kept=[];removed=[];rerouted=[]
    seen_leg_titles=set()
    for item in items:
        cat=field(item,'category').lower()
        if cat=='legislation':
            key=norm_title(item)
            if key and key in seen_leg_titles:
                removed.append({'category':cat,'source':field(item,'source'),'title':field(item,'title'),'reason':'exact-legislation-title-duplicate'})
                continue
            if key:seen_leg_titles.add(key)
        action,value=decision(item,cat)
        if action=='reject':
            removed.append({'category':cat,'source':field(item,'source'),'title':field(item,'title'),'reason':value});continue
        if action=='reroute':
            set_category(item,value);rerouted.append({'from':cat,'to':value,'source':field(item,'source'),'title':field(item,'title')})
        kept.append(item)
    by=defaultdict(list)
    for item in kept:by[field(item,'category').lower()].append(item)
    before={cat:max_streak(rows) for cat,rows in by.items() if cat in ROTATE}
    reordered={cat:balance_category(cat,rows) if cat in ROTATE else rows for cat,rows in by.items()}
    after={cat:max_streak(rows) for cat,rows in reordered.items() if cat in ROTATE}
    ideal={cat:optimal_streak_bound(rows) for cat,rows in reordered.items() if cat in ROTATE}
    cat_order=[]
    for item in kept:
        cat=field(item,'category').lower()
        if cat not in cat_order:cat_order.append(cat)
    for item in list(channel.findall('item')):channel.remove(item)
    for cat in cat_order:
        for item in reordered[cat]:channel.append(item)
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    report={'removedCount':len(removed),'reroutedCount':len(rerouted),'removed':removed,'rerouted':rerouted,
            'balancedTabs':sorted(ROTATE),'sourceStreakBefore':before,'sourceStreakAfter':after,'optimalStreakBound':ideal,
            'locationInventoryPreserved':{'local':'marketId','region':'region'}}
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
