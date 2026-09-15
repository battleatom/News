#!/usr/bin/env python3
"""V5.2-only final content guard.

Runs after the existing V5.1 refinement/routing chain. It is deliberately
conservative: remove only high-confidence category leaks, re-run strict
legislation separately, and reorder normal news tabs for publisher diversity
without discarding otherwise valid reporting.
"""
from __future__ import annotations
import json,re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

NEWS=Path('News')
REPORT=Path('/tmp/v52-content-guard.json')
PROTECTED={'top','x','boxoffice','legislation'}
ROTATE={'underreported','entertainment','world','us','presidential','federal','nm','local','region','nfl','technology','gaming','military'}
SPORT=re.compile(r'\b(nfl|nba|mlb|nhl|college football|high school football|football|basketball|baseball|hockey|soccer|golf|tennis|touchdown|quarterback|playoff|standings|scouting report)\b',re.I)
GAMING=re.compile(r'\b(video game|gaming|playstation|ps5|xbox|nintendo|switch 2|steam|game pass|esports|gameplay|dlc|game studio|game developer|pc gamer)\b',re.I)
TECH=re.compile(r'\b(ai|artificial intelligence|openai|chatgpt|anthropic|cybersecurity|software|hardware|semiconductor|nvidia|amd|intel|iphone|android|smartphone|laptop|gpu|cpu|data center|robotics?)\b',re.I)
WORLD=re.compile(r'\b(ukraine|russia|china|iran|israel|gaza|france|germany|united kingdom|britain|japan|india|canada|mexico|afghanistan|saudi|taiwan|nato|united nations|europe|africa|asia|middle east|international|foreign minister|prime minister)\b',re.I)
US_LOCAL=re.compile(r'\b(indiana|indianapolis|whiting,? indiana|iowa|west virginia)\b',re.I)
NM=re.compile(r'\b(new mexico|albuquerque|santa fe|las cruces|rio rancho|nmdot)\b',re.I)
REGION=re.compile(r'\b(arizona|colorado|utah|flagstaff|phoenix|denver|salt lake city|southern colorado|northern arizona)\b',re.I)
LOCAL=re.compile(r'\b(farmington|san juan county|aztec|bloomfield|kirtland|shiprock|four corners|durango|la plata county|cortez|montezuma county|navajo nation)\b',re.I)
TABLETOP=re.compile(r'\b(tabletop|board game|drinking game|party game|d&d-themed|dungeons?\s*&\s*dragons)\b',re.I)

def field(i,n): return (i.findtext(n) or '').strip()
def sid(i): return re.sub(r'[^a-z0-9]+','',(field(i,'source') or '').lower()) or 'unknown'
def headline(i):
    t=field(i,'title')
    return t.rsplit(' - ',1)[0] if ' - ' in t else t

def reject_reason(i,cat):
    t=headline(i)
    if cat in {'world','us','presidential','federal','nm','local','region'} and GAMING.search(t):
        return 'gaming-specialist-leak'
    if cat in {'world','us','presidential','federal','nm','local','region'} and SPORT.search(t):
        # NFL belongs only in NFL; geography tabs should not become sports feeds.
        return 'sports-leak'
    if cat=='world':
        if US_LOCAL.search(t) and not WORLD.search(t): return 'us-local-leak'
        if TECH.search(t) and not WORLD.search(t): return 'technology-leak'
    if cat=='nm' and not (NM.search(t) or field(i,'state').lower()=='new mexico'):
        # Keep statewide inventory metadata when present, but reject obvious non-NM sports above.
        if not field(i,'state'): return 'no-new-mexico-anchor'
    if cat=='region' and field(i,'state'):
        state=field(i,'state').lower()
        if state not in {'arizona','colorado','utah','new mexico'} and not (REGION.search(t) or LOCAL.search(t)):
            return 'outside-southwest-region'
    if cat=='gaming' and TABLETOP.search(t) and not GAMING.search(t): return 'non-video-game'
    return None

def rotate(rows):
    """Publisher rounds: best remaining card from every source before repeats."""
    buckets=defaultdict(list); order=[]
    for item in rows:
        s=sid(item)
        if s not in buckets: order.append(s)
        buckets[s].append(item)
    out=[]; round_no=0
    while True:
        added=False
        for s in order:
            if len(buckets[s])>round_no:
                out.append(buckets[s][round_no]); added=True
        if not added: break
        round_no+=1
    return out

def main():
    tree=ET.parse(NEWS); channel=tree.getroot().find('channel')
    if channel is None: raise SystemExit('RSS channel missing')
    items=list(channel.findall('item')); kept=[]; removed=[]
    for item in items:
        cat=field(item,'category').lower(); reason=reject_reason(item,cat)
        if reason:
            removed.append({'category':cat,'source':field(item,'source'),'title':field(item,'title'),'reason':reason})
        else: kept.append(item)
    by=defaultdict(list)
    for item in kept: by[field(item,'category').lower()].append(item)
    reordered={cat:rotate(rows) if cat in ROTATE else rows for cat,rows in by.items()}
    # Preserve category block order from the generated feed while changing only within-tab order.
    cat_order=[]
    for item in kept:
        cat=field(item,'category').lower()
        if cat not in cat_order: cat_order.append(cat)
    for item in list(channel.findall('item')): channel.remove(item)
    for cat in cat_order:
        for item in reordered[cat]: channel.append(item)
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    report={'removedCount':len(removed),'removed':removed,'rotatedTabs':sorted(ROTATE)}
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
