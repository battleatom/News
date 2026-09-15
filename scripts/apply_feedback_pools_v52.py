#!/usr/bin/env python3
"""V5.2 optimized D Pool enforcement.

Semantics stay intentional:
D  = exact article suppressed globally across every news tab.
NR = exact article suppressed only in the category where it was marked.
NW = exact article suppressed only in the category where it was marked.

Uses normalized set indexes instead of scanning every pool row for every article.
"""
from __future__ import annotations
import argparse,json,sys
import xml.etree.ElementTree as ET
from pathlib import Path
import apply_feedback_pools as base

REASONS=base.REASONS

def build_index(pools):
    idx={r:{'url':set(),'title_source':set()} for r in REASONS}
    for reason in REASONS:
        for row in pools.get(reason,[]):
            x=base.pool_identity(row); cat=x['category'] if reason!='D' else '*'
            if x['url_key']: idx[reason]['url'].add((cat,x['url_key']))
            if x['title_key'] and x['source_key']: idx[reason]['title_source'].add((cat,x['title_key'],x['source_key']))
    return idx

def match(item,idx):
    for reason in REASONS:
        cat='*' if reason=='D' else item['category']
        if item['url_key'] and (cat,item['url_key']) in idx[reason]['url']: return reason
        if item['title_key'] and item['source_key'] and (cat,item['title_key'],item['source_key']) in idx[reason]['title_source']: return reason
    return None

def apply(feed,pools):
    tree=ET.parse(feed); root=tree.getroot(); parent=root.find('channel') if root.tag.lower()=='rss' else root
    if parent is None: parent=root
    idx=build_index(pools); removed=[]
    for node in list(parent.findall('item')):
        item=base.item_identity(node); reason=match(item,idx)
        if not reason: continue
        parent.remove(node); removed.append({'reason':reason,'category':item['category'],'title':item['title'],'source':item['source']})
    if removed: tree.write(feed,encoding='utf-8',xml_declaration=True)
    return {'poolCounts':{r:len(pools.get(r,[])) for r in REASONS},'removedCount':len(removed),'removedByReason':{r:sum(x['reason']==r for x in removed) for r in REASONS},'removed':removed,'matching':'indexed-v52','semantics':{'D':'global exact article','NR':'category exact article','NW':'category exact article'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--feed',default='News');p.add_argument('--api',default=base.DEFAULT_API);p.add_argument('--require-remote',action='store_true');p.add_argument('--report',default='/tmp/v52-d-pool-report.json');a=p.parse_args()
    try: pools=base.fetch_pools(a.api)
    except Exception as e:
        if a.require_remote: print(f'D Pool fetch failed: {e}',file=sys.stderr);return 1
        pools={r:[] for r in REASONS}
    report=apply(Path(a.feed),pools);Path(a.report).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2));return 0
if __name__=='__main__': raise SystemExit(main())
