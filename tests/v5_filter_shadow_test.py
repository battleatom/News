#!/usr/bin/env python3
"""Shadow-test fresh authoritative V5 filters against the current V5 News snapshot."""
from __future__ import annotations
import json,sys,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from v5_global_filter import apply_pipeline
from v5_tab_filters import field,qualifies,RULES,RANKING_SURFACES,legislation_id
from v5_tab_dedupe import cross_tab_clusters,same_event
src=ROOT/'News'

def fake(title,category='legislation',link=''):
    i=ET.Element('item');ET.SubElement(i,'title').text=title;ET.SubElement(i,'category').text=category;ET.SubElement(i,'link').text=link;ET.SubElement(i,'description').text=title;return i
# Safety fixtures: similar official bills and templated stories must not collapse.
a=fake('H.R. 6509 — 119th Congress: SAFE Drugs Act of 2025','legislation','https://example.gov/bill/6509')
b=fake('H.R. 9183 — 119th Congress: Artificial Intelligence Environmental Impacts Act of 2026','legislation','https://example.gov/bill/9183')
assert legislation_id(a)!=legislation_id(b) and not same_event(a,b), 'distinct bill IDs collapsed'
c=fake('Jane Doe Obituary (1930 - 2026)','us','https://paper.test/jane')
d=fake('John Roe Obituary (1940 - 2026)','us','https://paper.test/john')
assert not same_event(c,d), 'templated obituaries collapsed'
with tempfile.TemporaryDirectory() as td:
    out=Path(td)/'News.filtered';report=apply_pipeline(str(src),str(out),str(ROOT/'v5-filter-shadow-report.json'))
    items=ET.parse(out).getroot().findall('.//item');failures=[]
    for item in items:
        cat=field(item,'category').lower()
        if cat in RANKING_SURFACES:continue
        if cat not in RULES or not qualifies(item,cat):failures.append((cat,field(item,'title')))
    residual=cross_tab_clusters(items);base=report['baselineCounts'];final=report['finalCounts']
    emptied=[c for c,n in base.items() if c not in RANKING_SURFACES and n>3 and final.get(c,0)==0]
    summary={'inputArticles':report['inputArticles'],'outputArticles':report['outputArticles'],'rerouted':report['rerouted'],'rejectedNoQualifiedTab':report['rejectedNoQualifiedTab'],'withinTabDuplicatesRemoved':report['withinTabDuplicatesRemoved'],'crossTabDuplicateEventsBeforeOwnership':report['crossTabDuplicateEvents'],'crossTabDuplicatesRemoved':report['crossTabDuplicatesRemoved'],'residualCrossTabDuplicateClusters':len(residual),'postFilterQualificationFailures':len(failures),'emptiedCategories':emptied,'baselineCounts':base,'finalCounts':final}
    print('=== V5 FRESH AUTHORITATIVE FILTER REPORT ===');print(json.dumps(summary,indent=2))
    print('\nTOP REROUTES:');[print(x) for x in report['routeChanges'][:25]]
    print('\nTOP REJECTIONS:');[print(x) for x in report['rejectedExamples'][:25]]
    print('\nTOP DUPLICATES:');[print(x) for x in report['withinTabDuplicateExamples'][:20]]
    print('\nTOP OWNERSHIP CHANGES:');[print(x) for x in report['ownershipChanges'][:20]]
    if failures:print('\nQUALIFICATION FAILURES:',failures[:15])
    if residual:
        print('\nRESIDUAL DUPLICATES:')
        for cluster in residual[:10]:print([(field(x,'category'),field(x,'title')) for x in cluster])
    if emptied:raise SystemExit('Active categories emptied: '+repr(emptied))
    if residual:raise SystemExit(f'Residual cross-tab duplicate clusters: {len(residual)}')
    if failures:raise SystemExit(f'Post-filter qualification failures: {len(failures)}')
