#!/usr/bin/env python3
"""Fast conservative cross-tab dedupe for ordinary subject tabs."""
import argparse, json, re, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROUTABLE={'world','us','presidential','federal','nm','local','region','technology','gaming','military','nfl'}
PRIORITY={'local':90,'nm':85,'presidential':82,'federal':80,'nfl':80,'gaming':76,'technology':74,'military':72,'region':68,'us':55,'world':50}
STOP={'the','and','for','from','with','that','this','after','before','into','over','about','new','says','said','news','live','are','was','were','has','have','had','its'}
def clean(v): return re.sub(r'\s+',' ',v or '').strip()
def cat(i): return clean(i.findtext('category')).lower()
def title(i):
    return re.sub(r'\s+(?:[-–—|:]\s*)?(?:Reuters|AP News|Associated Press|BBC|CNN|Fox News|NBC News|ABC News|CBS News|NPR|USA Today)\s*$','',clean(i.findtext('title')),flags=re.I)
def toks(s): return {w for w in re.findall(r'[a-z0-9]+',s.lower()) if len(w)>=3 and w not in STOP}
def curl(raw):
    raw=clean(raw)
    if not raw:return ''
    try:
        p=urlsplit(raw); return urlunsplit(((p.scheme or 'https').lower(),p.netloc.lower().removeprefix('www.'),re.sub(r'/+$','',p.path) or '/','',''))
    except Exception:return raw.lower()
def related(primary,other):
    rel=primary.find('relatedArticles')
    if rel is None: rel=ET.SubElement(primary,'relatedArticles')
    key=curl(other.findtext('link')) or title(other).lower()
    existing={curl(x.findtext('link')) or title(x).lower() for x in rel.findall('article')}
    if not key or key in existing:return False
    ar=ET.SubElement(rel,'article')
    for tag in ('title','link','source','pubDate'):
        v=clean(other.findtext(tag))
        if v: ET.SubElement(ar,tag).text=v
    ET.SubElement(ar,'crossTabFrom').text=cat(other); return True

def scan(items):
    sig=[]
    for i in items:
        sig.append((cat(i),curl(i.findtext('link')),toks(title(i)),toks(clean(i.findtext('description')))))
    parent=list(range(len(items))); reasons={}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b: parent[b]=a
    active=[n for n,s in enumerate(sig) if s[0] in ROUTABLE]
    for pos,a in enumerate(active):
        ca,ua,ta,da=sig[a]
        for b in active[pos+1:]:
            cb,ub,tb,db=sig[b]
            if ca==cb: continue
            reason=''
            if ua and ua==ub: reason='same-url'
            elif ta and tb:
                shared=len(ta&tb); ratio=shared/max(1,min(len(ta),len(tb)))
                if min(len(ta),len(tb))>=5 and shared>=5 and ratio>=.88: reason='near-identical-title'
                elif len(da)>=10 and len(db)>=10:
                    bs=len(da&db); br=bs/max(1,min(len(da),len(db)))
                    if shared>=4 and ratio>=.72 and bs>=8 and br>=.82: reason='strong-title-body-overlap'
            if reason: union(a,b); reasons[(a,b)]=reason
    groups=defaultdict(list)
    for i in range(len(items)): groups[find(i)].append(i)
    return [g for g in groups.values() if len(g)>1],reasons

def run(feed,report,apply):
    tree=ET.parse(feed); channel=tree.getroot().find('channel')
    if channel is None: raise SystemExit('Invalid RSS: missing channel')
    items=list(channel.findall('item')); before=Counter(cat(i) for i in items); groups,reasons=scan(items)
    removed=set(); attached=0; rows=[]
    for g in groups:
        winner=max(g,key=lambda x:(PRIORITY.get(cat(items[x]),0),min(len(clean(items[x].findtext('description'))),2000),len(title(items[x]))))
        gone=[]
        for x in g:
            if x==winner: continue
            attached+=int(related(items[winner],items[x])); removed.add(x); gone.append({'title':title(items[x]),'category':cat(items[x])})
        rows.append({'kept':title(items[winner]),'primaryCategory':cat(items[winner]),'removed':gone,'size':len(g)})
    final=[i for n,i in enumerate(items) if n not in removed]; after=Counter(cat(i) for i in final)
    excessive={c:{'before':before[c],'after':after[c]} for c in ROUTABLE if before[c]>=10 and after[c]<max(8,int(before[c]*.75))}
    if excessive: raise SystemExit('Would over-prune categories: '+json.dumps(excessive,sort_keys=True))
    if apply:
        for i in list(channel.findall('item')): channel.remove(i)
        for i in final: channel.append(i)
        tree.write(feed,encoding='utf-8',xml_declaration=True)
    residual,_=scan(final)
    out={'mode':'apply' if apply else 'dry-run','generatedAt':datetime.now(timezone.utc).isoformat(),'inputArticles':len(items),'outputArticles':len(final),'crossTabPairsDetected':len(reasons),'crossTabDuplicatesRemoved':len(removed),'supportingLinksAttached':attached,'categoryDrops':{c:before[c]-after[c] for c in sorted(ROUTABLE) if before[c]!=after[c]},'clusters':rows,'residualStrongCrossTabClusters':len(residual),'policy':{'editorialSurfacesExcluded':['top','underreported','x','boxoffice','legislation','entertainment'],'maxCategoryReduction':'25%'}}
    Path(report).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('inputArticles','outputArticles','crossTabPairsDetected','crossTabDuplicatesRemoved','categoryDrops','residualStrongCrossTabClusters')},indent=2))
    if residual: raise SystemExit(f'{len(residual)} residual strong cross-tab clusters remain')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--feed',default='News'); p.add_argument('--report',default='cross-tab-integrity-report.json'); p.add_argument('--apply',action='store_true'); a=p.parse_args(); run(a.feed,a.report,a.apply)
if __name__=='__main__': main()
