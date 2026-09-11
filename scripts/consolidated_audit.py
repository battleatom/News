#!/usr/bin/env python3
"""Audit every article in a candidate News feed against routing/source/duplicate policy.
Read-only with respect to News; writes consolidated-audit-report.json.
"""
from __future__ import annotations
import json, re, sys, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from classify_live_feed import classify
from verify_feed import same_event, category, title
NEWS=ROOT/'News'; OUT=ROOT/'consolidated-audit-report.json'

def main():
    root=ET.parse(NEWS).getroot(); items=root.findall('.//item')
    by=defaultdict(list); decisions=[]; failures=[]
    for i,item in enumerate(items):
        cat=category(item); by[cat].append(item); d=classify(item)
        row={'index':i,'title':title(item),'source':(item.findtext('source') or '').strip(),'category':cat,'decision':d.get('action'),'suggested':d.get('category'),'confidence':d.get('confidence'),'reason':d.get('reason')}
        decisions.append(row)
        if d.get('action')=='reject': failures.append({'type':'source','article':row})
        if cat=='federal' and d.get('action')=='reroute' and d.get('category')!='federal' and float(d.get('confidence') or 0)>=.80: failures.append({'type':'routing','article':row})
    duplicates=[]
    for cat,group in by.items():
        for a in range(len(group)):
            for b in range(a+1,len(group)):
                if same_event(group[a],group[b]): duplicates.append({'category':cat,'a':title(group[a]),'b':title(group[b])})
    report={'totalArticles':len(items),'categoryCounts':dict(sorted((k,len(v)) for k,v in by.items())),'decisionCounts':dict(Counter(x['decision'] for x in decisions)),'failures':failures,'duplicatePairs':duplicates,'articles':decisions}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('totalArticles','categoryCounts','decisionCounts')},indent=2)); print('failures',len(failures),'duplicatePairs',len(duplicates))
    if failures or duplicates: raise SystemExit(2)
if __name__=='__main__': main()
