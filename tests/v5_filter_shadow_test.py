#!/usr/bin/env python3
"""Shadow-test fresh authoritative V5 filters against the current V5 News snapshot."""
from __future__ import annotations
import json,sys,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from v5_global_filter import apply_pipeline,PROTECTED_CATEGORIES,direct_presidential_story,direct_federal_story,military_headline_anchor,current_tab_contextual_keep,LOW_VALUE_GEO_HEADLINE
from v5_tab_filters import field,qualifies,RULES,RANKING_SURFACES,EDITORIAL_OVERLAYS,legislation_id,best_tab,tab_filter_decision,obvious_noise
from v5_tab_dedupe import cross_tab_clusters,same_event
src=ROOT/'News'

def fake(title,category='legislation',link='',description=None,**fields):
    i=ET.Element('item');ET.SubElement(i,'title').text=title;ET.SubElement(i,'category').text=category;ET.SubElement(i,'link').text=link;ET.SubElement(i,'description').text=description or title
    for k,v in fields.items():ET.SubElement(i,k).text=str(v)
    return i

def protected_signature(path):
    items=ET.parse(path).getroot().findall('.//item')
    return [(field(i,'category').lower(),field(i,'title'),field(i,'link')) for i in items if field(i,'category').lower() in PROTECTED_CATEGORIES]

# Duplicate safety: similar official bills and templated stories must not collapse.
a=fake('H.R. 6509 — 119th Congress: SAFE Drugs Act of 2025','legislation','https://example.gov/bill/6509')
b=fake('H.R. 9183 — 119th Congress: Artificial Intelligence Environmental Impacts Act of 2026','legislation','https://example.gov/bill/9183')
assert legislation_id(a)!=legislation_id(b) and not same_event(a,b), 'distinct bill IDs collapsed'
assert best_tab(b)[0]=='legislation', 'structured bill lost canonical legislation ownership'
c=fake('Jane Doe Obituary (1930 - 2026)','us','https://paper.test/jane')
d=fake('John Roe Obituary (1940 - 2026)','us','https://paper.test/john')
assert not same_event(c,d), 'templated obituaries collapsed'

# Topic/ownership regressions observed in live V5.
assert best_tab(fake('Ukraine hit by Russian missile strike as military operation expands','nfl'))[0]=='military', 'military operation did not prefer Military'
assert best_tab(fake('A long summer: how trade war and wildfires hit household prices','underreported'))[0] != 'military', 'metaphorical/economic war falsely became Military'
assert best_tab(fake('Trump administration proposes new immigration rule','presidential'))[0]=='presidential', 'Trump administration story lost Presidential ownership'
assert direct_presidential_story(fake('Trump says he would consider a pardon','presidential')), 'direct Trump headline contract failed'
assert not military_headline_anchor(fake("The inside story of 9/11, told by an advisor on Air Force One",'world')), 'Air Force One falsely counted as Military evidence'
assert best_tab(fake('US Senate negotiators advance federal funding package','federal'))[0]=='federal', 'US Senate story lost Federal ownership'
assert direct_federal_story(fake("House Speaker says Congress will vote next week",'us')), 'House/Speaker federal headline contract failed'
assert best_tab(fake('California Supreme Court hears state bail challenge','us'))[0] != 'federal', 'state supreme court falsely became Federal'
assert best_tab(fake('Farmington City Council approves water project','local'))[0]=='local', 'Farmington story lost Local ownership'
assert best_tab(fake('Albuquerque officials announce statewide New Mexico initiative','nm'))[0]=='nm', 'New Mexico story lost NM ownership'
assert best_tab(fake('Virginia Tech opens football season against rival','us'))[0] != 'technology', 'Virginia Tech false-positive Technology match'
assert best_tab(fake('Georgia football prepares for Western Kentucky','region'))[0] != 'nfl', 'college football falsely became NFL'
assert best_tab(fake('49ers announce injury update before Seahawks game','nfl'))[0]=='nfl', '49ers alias failed NFL ownership'
assert best_tab(fake('Chicago mayor discusses keeping the Bears in the city','us'))[0] != 'nfl', 'ambiguous Bears mention falsely became NFL'
assert best_tab(fake('Casino operator expands sportsbook and slot floor','gaming'))[0] != 'gaming', 'gambling falsely became Gaming'

# Dynamic Local / Region inventory is already geography-validated upstream and must survive the final filter.
local_tagged=fake('City council approves downtown safety changes','local',marketId='seattle-wa',marketCity='Seattle',marketState='WA')
region_tagged=fake('Wildfire restrictions lifted after rainfall','region',state='Colorado',region='mountain')
assert current_tab_contextual_keep(local_tagged,'local'), 'validated Local market metadata was not preserved'
assert current_tab_contextual_keep(region_tagged,'region'), 'validated Region metadata was not preserved'

# Broad-tab contextual preservation catches valid civic stories that do not use the narrow scorer vocabulary.
assert current_tab_contextual_keep(fake("Senegal's President to meet IMF chief in Washington",'world'),'world'), 'foreign civic World story was not preserved'
assert current_tab_contextual_keep(fake('How proposed census changes could affect states and voters','us'),'us'), 'national U.S. civic story was not preserved'
assert current_tab_contextual_keep(fake('Microsoft rolls out new AI security tools','technology'),'technology'), 'strong Technology headline was not preserved'
assert current_tab_contextual_keep(fake('Nintendo announces new Switch game release','gaming'),'gaming'), 'strong Gaming headline was not preserved'
assert LOW_VALUE_GEO_HEADLINE.search('Santa Fe-area food service inspections, July 27-Aug. 2'), 'low-value geography guard missed inspection roundup'
assert LOW_VALUE_GEO_HEADLINE.search('Vote: New Mexico high school football star of Week 4'), 'low-value geography guard missed school-sports poll'

# Underreported is an editorial overlay, not a mutually-exclusive subject owner.
u=fake('Watchdog investigation finds rural hospital Medicaid failures','underreported')
assert tab_filter_decision(u)['action']=='keep', 'qualified Underreported investigation was stripped from editorial overlay'

before_protected=protected_signature(src)
with tempfile.TemporaryDirectory() as td:
    out=Path(td)/'News.filtered';report=apply_pipeline(str(src),str(out),str(ROOT/'v5-filter-shadow-report.json'))
    after_protected=protected_signature(out)
    if before_protected!=after_protected:raise SystemExit('Protected Box Office/Entertainment content changed')
    items=ET.parse(out).getroot().findall('.//item');failures=[]
    for item in items:
        cat=field(item,'category').lower()
        if cat in RANKING_SURFACES or cat in PROTECTED_CATEGORIES:continue
        if cat in EDITORIAL_OVERLAYS:
            if obvious_noise(item):failures.append((cat,field(item,'title')))
            continue
        # Strong current-tab context can be valid even when the generic phrase scorer intentionally stays
        # below threshold. This covers validated dynamic geography and conservative broad/specialist fallbacks.
        if current_tab_contextual_keep(item,cat):continue
        if cat=='presidential' and direct_presidential_story(item):continue
        if cat not in RULES or not qualifies(item,cat):failures.append((cat,field(item,'title')))
    residual=cross_tab_clusters(items);base=report['baselineCounts'];final=report['finalCounts']
    protected=set(RANKING_SURFACES)|set(EDITORIAL_OVERLAYS)|set(PROTECTED_CATEGORIES)
    emptied=[c for c,n in base.items() if c not in protected and n>3 and final.get(c,0)==0]
    summary={'inputArticles':report['inputArticles'],'outputArticles':report['outputArticles'],'rerouted':report['rerouted'],'rejectedNoQualifiedTab':report['rejectedNoQualifiedTab'],'withinTabDuplicatesRemoved':report['withinTabDuplicatesRemoved'],'crossTabDuplicateEventsBeforeOwnership':report['crossTabDuplicateEvents'],'crossTabDuplicatesRemoved':report['crossTabDuplicatesRemoved'],'residualCrossTabDuplicateClusters':len(residual),'postFilterQualificationFailures':len(failures),'protectedBoxOfficeItems':len(before_protected),'boxOfficePreservedExactly':before_protected==after_protected,'emptiedCategories':emptied,'baselineCounts':base,'finalCounts':final}
    print('=== V5 FRESH AUTHORITATIVE FILTER REPORT ===');print(json.dumps(summary,indent=2))
    print('\nTOP REROUTES:');[print(x) for x in report['routeChanges'][:30]]
    print('\nTOP REJECTIONS:');[print(x) for x in report['rejectedExamples'][:30]]
    print('\nTOP DUPLICATES:');[print(x) for x in report['withinTabDuplicateExamples'][:20]]
    print('\nTOP OWNERSHIP CHANGES:');[print(x) for x in report['ownershipChanges'][:20]]
    if failures:print('\nQUALIFICATION FAILURES:',failures[:15])
    if residual:
        print('\nRESIDUAL DUPLICATES:')
        for cluster in residual[:10]:print([(field(x,'category'),field(x,'title')) for x in cluster])
    if emptied:raise SystemExit('Active categories emptied: '+repr(emptied))
    if residual:raise SystemExit(f'Residual cross-tab duplicate clusters: {len(residual)}')
    if failures:raise SystemExit(f'Post-filter qualification failures: {len(failures)}')
