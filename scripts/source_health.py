#!/usr/bin/env python3
"""Generate a lightweight source/category health report from the built RSS feed."""
from __future__ import annotations
import json, statistics, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

FEED=Path('News'); OUT=Path('source-health.json')

def clean(v): return ' '.join((v or '').split())

def run(feed=FEED,out=OUT):
    root=ET.parse(feed).getroot(); items=root.findall('.//item')
    by_source=Counter(); by_cat=Counter(); source_cats=defaultdict(Counter); headline_fallback=Counter(); total_fallback=0
    for i in items:
        src=clean(i.findtext('source')) or 'Unknown'; cat=clean(i.findtext('category')).lower() or 'unknown'
        by_source[src]+=1; by_cat[cat]+=1; source_cats[src][cat]+=1
        fallback=(clean(i.findtext('briefSource')).lower()=='headline-fallback')
        if fallback: headline_fallback[src]+=1; total_fallback+=1
    category_diversity={}
    for cat,n in by_cat.items():
        counts=Counter(clean(i.findtext('source')) or 'Unknown' for i in items if clean(i.findtext('category')).lower()==cat)
        top=counts.most_common(1)[0][1] if counts else 0
        category_diversity[cat]={'articles':n,'sources':len(counts),'topSourceShare':round(top/max(1,n),3)}
    sources={}
    for src,n in by_source.items():
        sources[src]={'articles':n,'categories':dict(source_cats[src]),'headlineFallbackRate':round(headline_fallback[src]/n,3)}
    report={
        'generatedAt':datetime.now(timezone.utc).isoformat(),
        'articles':len(items),'distinctSources':len(by_source),
        'headlineFallbackRate':round(total_fallback/max(1,len(items)),3),
        'categoryDiversity':category_diversity,
        'sources':dict(sorted(sources.items(),key=lambda kv:(-kv[1]['articles'],kv[0].lower()))),
        'warnings':[]
    }
    for cat,v in category_diversity.items():
        if v['articles']>=10 and v['sources']<3: report['warnings'].append(f'{cat}: low source diversity ({v["sources"]} sources)')
        if v['articles']>=10 and v['topSourceShare']>.55: report['warnings'].append(f'{cat}: source concentration {v["topSourceShare"]:.0%}')
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"Source health: {len(items)} articles, {len(by_source)} sources, {len(report['warnings'])} warning(s)")
    return report
if __name__=='__main__': run()
