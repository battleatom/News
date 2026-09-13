#!/usr/bin/env python3
"""Final fail-closed audit for the V5 release candidate."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
NEWS=ROOT/'News'
OUT=ROOT/'v5-final-audit-report.json'
EXPECTED_X=['Health','Technology & AI','Celebrities & Public Figures','World','Politics & Government','Entertainment','Sports','Business & Economy','Gaming','Science']
REQUIRED={'top','nfl','x','underreported','entertainment','world','us','presidential','federal','legislation','nm','technology','gaming','military'}
GENERIC_PATTERNS=[r'^world news$',r'^latest news$',r'^breaking news$',r'^news$',r'^home$',r'^homepage$',r'^sports$',r'^technology$',r'^entertainment$']
CANNED_WHY=['This matters because it could affect people','This matters because it affects people','This story matters because']

def txt(i,t): return (i.findtext(t) or '').strip()
def norm(s): return re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).strip()
def fail(errors,msg): errors.append(msg)

def main():
    errors=[]; warnings=[]
    if not NEWS.exists(): raise SystemExit('V5 FINAL AUDIT FAILED: News feed missing')
    items=ET.parse(NEWS).getroot().findall('.//item')
    counts=Counter(txt(i,'category') for i in items)
    for c in sorted(REQUIRED):
        if counts[c]==0: fail(errors,f'{c}: empty required category')

    seen_links=defaultdict(list); seen_titles=defaultdict(list)
    for n,i in enumerate(items):
        title,link,cat=txt(i,'title'),txt(i,'link'),txt(i,'category')
        if not title or not link or not cat: fail(errors,f'item {n}: missing title/link/category')
        if link:
            p=urlparse(link)
            if p.scheme not in {'http','https'} or not p.netloc: fail(errors,f'{cat}: invalid URL {link}')
            seen_links[link].append((cat,title))
        nt=norm(title)
        if nt: seen_titles[nt].append((cat,title))
        if any(re.fullmatch(p,nt,re.I) for p in GENERIC_PATTERNS): fail(errors,f'{cat}: generic landing-page title: {title}')
        why=txt(i,'whyItMatters') or txt(i,'why')
        if why and any(x.lower() in why.lower() for x in CANNED_WHY): fail(errors,f'{cat}: legacy canned Why It Matters: {title}')
        brief=txt(i,'contentBrief') or txt(i,'summary') or txt(i,'description')
        if brief and brief.rstrip().endswith('...'): fail(errors,f'{cat}: visibly truncated brief: {title}')

    dup_links={k:v for k,v in seen_links.items() if len(v)>1}
    if dup_links: fail(errors,f'{len(dup_links)} exact duplicate URL(s) remain across feed')
    duplicate_titles={k:v for k,v in seen_titles.items() if len(v)>1 and len(k.split())>=5}
    if duplicate_titles: warnings.append(f'{len(duplicate_titles)} normalized title group(s) repeat; browser/event gates must confirm presentation dedupe')

    x=[i for i in items if txt(i,'category')=='x']
    topics=[txt(i,'xTopic') for i in x]
    if topics!=EXPECTED_X: fail(errors,f'X topic sequence invalid: {topics}')

    ent=[i for i in items if txt(i,'category')=='entertainment']
    for i in ent:
        if txt(i,'entertainmentSafety') not in {'clean','dirty'}: fail(errors,f'Entertainment unclassified: {txt(i,"title")}')
        if not txt(i,'entertainmentLabel') or not txt(i,'entertainmentScore'): fail(errors,f'Entertainment ranking metadata missing: {txt(i,"title")}')

    legislation=[i for i in items if txt(i,'category')=='legislation']
    official_hosts=('congress.gov','senate.gov','house.gov','govinfo.gov','legiscan.com')
    for i in legislation:
        host=urlparse(txt(i,'link')).netloc.lower()
        if not any(host==h or host.endswith('.'+h) for h in official_hosts): warnings.append(f'Legislation provenance review: {txt(i,"title")} -> {host}')

    report={'status':'pass' if not errors else 'fail','feedItems':len(items),'categoryCounts':dict(sorted(counts.items())),'errors':errors,'warnings':warnings,'duplicateUrlGroups':len(dup_links),'duplicateTitleGroups':len(duplicate_titles),'xTopics':topics}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if errors:
        print(json.dumps(report,indent=2,ensure_ascii=False)); raise SystemExit(f'V5 FINAL AUDIT FAILED: {len(errors)} error(s)')
    print('V5 FINAL CONTENT AUDIT PASSED')
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
