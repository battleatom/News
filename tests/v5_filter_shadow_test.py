#!/usr/bin/env python3
"""Shadow-test the fresh V5 routing stack against the repository's current live News feed."""
from __future__ import annotations
import json,sys,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from v5_global_filter import apply_pipeline
from v5_tab_filters import field,qualifies,RULES,RANKING_SURFACES,SPECIAL_SURFACES
from v5_tab_dedupe import cross_tab_clusters
src=ROOT/'News'
with tempfile.TemporaryDirectory() as td:
    out=Path(td)/'News.filtered'; report=apply_pipeline(str(src),str(out),str(ROOT/'v5-filter-shadow-report.json'))
    items=ET.parse(out).getroot().findall('.//item'); failures=[]
    for item in items:
        cat=field(item,'category').lower()
        if cat in RANKING_SURFACES or cat in SPECIAL_SURFACES: continue
        if cat in RULES and not qualifies(item,cat): failures.append((cat,field(item,'title')))
    residual=cross_tab_clusters(items); base=report['baselineCounts']; final=report['finalCounts']
    emptied=[cat for cat,n in base.items() if cat not in {'top','x','boxoffice'} and n>1 and final.get(cat,0)==0]
    summary={'inputArticles':report['inputArticles'],'outputArticles':report['outputArticles'],'rerouted':report['rerouted'],'withinTabDuplicatesRemoved':report['withinTabDuplicatesRemoved'],'crossTabDuplicateEventsBeforeOwnership':report['crossTabDuplicateEvents'],'crossTabDuplicatesRemoved':report['crossTabDuplicatesRemoved'],'unresolved':report['unresolved'],'residualCrossTabDuplicateClusters':len(residual),'postFilterQualificationFailures':len(failures),'emptiedCategories':emptied,'baselineCounts':base,'finalCounts':final}
    print('=== V5 FRESH FILTER SHADOW REPORT ==='); print(json.dumps(summary,indent=2))
    print('\nTOP REROUTES:'); [print(row) for row in report['routeChanges'][:30]]
    print('\nTOP CROSS-TAB OWNERSHIP CHANGES:'); [print(row) for row in report['ownershipChanges'][:30]]
    print('\nTOP WITHIN-TAB DUPLICATES:'); [print(row) for row in report['withinTabDuplicateExamples'][:20]]
    if failures[:10]: print('\nQUALIFICATION FAILURES:',failures[:10])
    if residual[:10]:
        print('\nRESIDUAL DUPLICATE CLUSTERS:')
        for c in residual[:10]: print([(field(i,'category'),field(i,'title')) for i in c])
    if emptied: raise SystemExit('Shadow filter emptied active categories: '+repr(emptied))
    if residual: raise SystemExit(f'Residual cross-tab duplicate clusters remain: {len(residual)}')
    if failures: raise SystemExit(f'Post-filter qualification failures remain: {len(failures)}')
