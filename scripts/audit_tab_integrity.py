#!/usr/bin/env python3
import json,re,xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from classify_live_feed import classify

FEED=Path(__file__).resolve().parents[1]/'News'
SPORT=re.compile(r'\b(nfl|football|quarterback|touchdown|wide receiver|running back|linebacker|super bowl|playoffs?|coach|roster|draft|touchdowns?)\b',re.I)
WAR=re.compile(r'\b(war|airstrike|airstrikes|missile|missiles|troops|military|houthi|houthis|iran|israel|lebanon|ukraine|russia|ceasefire|strike|strikes|invasion|navy|army|pentagon)\b',re.I)
TECH=re.compile(r'\b(ai|artificial intelligence|software|cyber|chip|semiconductor|apple|google|microsoft|openai|android|iphone|computer|technology)\b',re.I)
GAMING=re.compile(r'\b(playstation|xbox|nintendo|steam|gaming|video game|console|game studio|esports)\b',re.I)
LEG=re.compile(r'\b(bill|legislation|lawmakers?|senate|house bill|act|statute|ordinance)\b',re.I)
PRES=re.compile(r'\b(president|trump|white house|vance|administration)\b',re.I)
LOCAL=re.compile(r'\b(farmington|san juan county|four corners|durango|aztec|bloomfield)\b',re.I)

items=ET.parse(FEED).getroot().findall('./channel/item')
by=defaultdict(list)
for i in items: by[(i.findtext('category') or '').strip().lower()].append(i)

def text(i): return ' '.join([(i.findtext('title') or ''),(i.findtext('description') or '')])
def title(i): return (i.findtext('title') or '').strip()

def flags(i,cat):
    t=text(i); out=[]
    if cat!='nfl' and SPORT.search(t): out.append('sports-leak')
    if cat not in {'military','world','top','underreported','x'} and WAR.search(t): out.append('war-leak')
    if cat!='gaming' and GAMING.search(t): out.append('gaming-leak')
    if cat!='technology' and TECH.search(t): out.append('tech-leak')
    if cat!='legislation' and LEG.search(t): out.append('legislation-leak')
    if cat not in {'presidential','top','x'} and PRES.search(t): out.append('presidential-overlap')
    if cat not in {'local','nm','region','top'} and LOCAL.search(t): out.append('locality-leak')
    return out

report={'total':len(items),'tabs':{},'highConfidenceReroutes':[],'heuristicLeaks':[]}
for cat,group in sorted(by.items()):
    cnt=Counter(); samples=defaultdict(list); rer=[]
    for i in group:
        d=classify(i)
        if d.get('action')=='reroute' and float(d.get('confidence') or 0)>=0.72 and d.get('category') and d.get('category')!=cat:
            row={'from':cat,'to':d['category'],'confidence':d.get('confidence'),'title':title(i),'evidence':d.get('evidence',[])[:5]}
            rer.append(row); report['highConfidenceReroutes'].append(row)
        for f in flags(i,cat):
            cnt[f]+=1
            if len(samples[f])<8: samples[f].append(title(i))
            report['heuristicLeaks'].append({'category':cat,'flag':f,'title':title(i)})
    report['tabs'][cat]={'count':len(group),'flags':dict(cnt),'samples':dict(samples),'reroutes':rer[:12]}
print(json.dumps(report,indent=2,ensure_ascii=False))
