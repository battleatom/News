#!/usr/bin/env python3
"""Persistent feedback enforcement with conservative self-learning.

D  = exact article suppressed globally.
NR = exact article suppressed in its original category; when a target_category exists,
     repeated high-confidence origin->target examples teach automatic routing.
NW = exact article suppressed in category; repeated generic/landing-title patterns teach
     conservative rejection.

Learning is deliberately bounded: routing requires >=2 corroborating examples for the
same origin/target plus a reusable token signature. Single clicks never create broad rules.
"""
from __future__ import annotations
import argparse,json,re,sys
import xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
import apply_feedback_pools as base

REASONS=base.REASONS
STOP={'the','and','for','with','from','this','that','news','latest','update','updates','report','reports','page','new'}

def norm(v): return re.sub(r'\s+',' ',str(v or '').lower()).strip()
def toks(v): return {x for x in re.findall(r'[a-z0-9]+',norm(v)) if len(x)>=4 and x not in STOP}

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

def learn(pools):
    """Derive only corroborated, reversible rules from feedback snapshots."""
    routes=defaultdict(list)
    for row in pools.get('NR',[]):
        origin=norm(row.get('original_category') or row.get('category'))
        target=norm(row.get('target_category'))
        if origin and target and origin!=target:
            routes[(origin,target)].append(row)

    learned_routes=[]
    for (origin,target),rows in routes.items():
        if len(rows)<2: continue
        counts=Counter()
        for row in rows:
            for token in toks(row.get('title','')): counts[token]+=1
        signature={token for token,n in counts.items() if n>=2}
        if signature:
            learned_routes.append({'origin':origin,'target':target,'tokens':sorted(signature),'examples':len(rows)})

    # NW learns only repeated structural page-title patterns, never topical censorship.
    nw_titles=[norm(r.get('title')) for r in pools.get('NW',[])]
    structural=[]
    patterns=[
      ('generic-news',r'^(?:nfl )?news(?:\s*&\s*analysis)?$'),
      ('profile-updates',r'^.+? news,? rumors,? (?:&|and) updates$'),
      ('paginated-index',r'^.+?\s*\|\s*page\s+\d+'),
      ('breaking-news',r'^breaking news$')
    ]
    for name,pat in patterns:
        hits=sum(bool(re.search(pat,t,re.I)) for t in nw_titles)
        if hits>=2: structural.append({'name':name,'pattern':pat,'examples':hits})
    return {'routes':learned_routes,'nwStructural':structural}

def set_category(node,value):
    x=node.find('category')
    if x is None: x=ET.SubElement(node,'category')
    x.text=value

def apply(feed,pools):
    tree=ET.parse(feed); root=tree.getroot(); parent=root.find('channel') if root.tag.lower()=='rss' else root
    if parent is None: parent=root
    idx=build_index(pools); learned=learn(pools); removed=[]; routed=[]
    for node in list(parent.findall('item')):
        item=base.item_identity(node); reason=match(item,idx)
        if reason:
            parent.remove(node); removed.append({'reason':reason,'category':item['category'],'title':item['title'],'source':item['source']}); continue
        title_tokens=toks(item['title'])
        route=None
        for rule in learned['routes']:
            if item['category']==rule['origin'] and title_tokens.intersection(rule['tokens']):
                route=rule; break
        if route:
            old=item['category']; set_category(node,route['target'])
            routed.append({'from':old,'to':route['target'],'title':item['title'],'learnedFrom':route['examples']}); continue
        low=norm(item['title'])
        if any(re.search(rule['pattern'],low,re.I) for rule in learned['nwStructural']):
            parent.remove(node); removed.append({'reason':'NW-learned','category':item['category'],'title':item['title'],'source':item['source']})
    if removed or routed: tree.write(feed,encoding='utf-8',xml_declaration=True)
    return {'poolCounts':{r:len(pools.get(r,[])) for r in REASONS},'removedCount':len(removed),'removedByReason':{r:sum(x['reason']==r for x in removed) for r in REASONS},'removed':removed,'learned':learned,'learnedRoutedCount':len(routed),'learnedRouted':routed,'matching':'indexed-self-learning-v1','semantics':{'D':'global exact article','NR':'category exact + corroborated route learning','NW':'category exact + repeated structural learning'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--feed',default='News');p.add_argument('--api',default=base.DEFAULT_API);p.add_argument('--require-remote',action='store_true');p.add_argument('--report',default='/tmp/v52-d-pool-report.json');a=p.parse_args()
    try: pools=base.fetch_pools(a.api)
    except Exception as e:
        if a.require_remote: print(f'D Pool fetch failed: {e}',file=sys.stderr);return 1
        pools={r:[] for r in REASONS}
    report=apply(Path(a.feed),pools);Path(a.report).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2));return 0
if __name__=='__main__': raise SystemExit(main())
