#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, re, sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v5_tab_filters import field, qualifies, TAB_TOPICS
from v5_global_filter import safe_best_tab

TABS = [
    'top','x','underreported','entertainment','world','us','presidential','federal',
    'legislation','nm','local','region','nfl','technology','gaming','military'
]
OWNERSHIP = {'world','us','presidential','federal','legislation','nm','local','region','nfl','technology','gaming','military'}

ENT_RE = re.compile(r"\b(actor|actress|singer|rapper|musician|celebrity|hollywood|film|movie|television|tv|series|netflix|hbo|disney\+|album|song|tour|concert|music|entertainment|emmy|grammy|oscar|award|director|producer)\b", re.I)
SPORT_RE = re.compile(r"\b(nfl|nba|mlb|nhl|football|basketball|baseball|hockey|soccer|golf|tennis|score|touchdown|quarterback|coach)\b", re.I)
GAMING_RE = re.compile(r"\b(video game|gaming|playstation|ps5|xbox|nintendo|switch 2|steam|game pass|esports|gameplay|dlc|game studio|game developer)\b", re.I)
TECH_RE = re.compile(r"\b(ai|artificial intelligence|openai|chatgpt|anthropic|cyber|software|hardware|semiconductor|nvidia|amd|intel|iphone|android|smartphone|laptop|cpu|gpu|pc|cloud|robot|technology|tech)\b", re.I)
MIL_RE = re.compile(r"\b(military|pentagon|army|navy|air force|marine|troops|missile|airstrike|drone strike|warship|combat|battlefield|invasion|ceasefire|defense department|centcom|fighter jet|f-35|munitions|weapon system)\b", re.I)
PRES_RE = re.compile(r"\b(president trump|donald trump|trump administration|white house|executive order|press secretary|oval office)\b", re.I)
FED_RE = re.compile(r"\b(congress|senate|house of representatives|supreme court|federal court|federal judge|fbi|doj|dhs|irs|epa|treasury department|federal agency|federal government)\b", re.I)
NM_RE = re.compile(r"\b(new mexico|albuquerque|santa fe|las cruces|rio rancho|nmdot)\b", re.I)
LOCAL_RE = re.compile(r"\b(farmington|san juan county|aztec|bloomfield|kirtland|shiprock|four corners|durango|la plata county|cortez|montezuma county|navajo nation)\b", re.I)


def norm_title(s):
    s=(s or '').lower()
    s=re.sub(r"\s+-\s+[^-]{2,50}$",'',s)
    s=re.sub(r'[^a-z0-9 ]+',' ',s)
    return ' '.join(s.split())

def norm_url(s):
    try:
        p=urlsplit(s or '')
        return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),'',''))
    except Exception:
        return s or ''

def norm_legislation_url(s):
    """Preserve official-record query parameters used to identify a specific bill.

    Normal news URLs drop query strings to ignore tracking parameters. Official
    legislature URLs can encode the bill identity in the query itself (for example,
    NM Legislature Chamber/LegNo/LegType/year). Stripping that query makes distinct
    bills look like one exact duplicate group, so legislation uses this stricter key.
    """
    try:
        p=urlsplit(s or '')
        return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),p.query,''))
    except Exception:
        return s or ''

def source_id(s): return re.sub(r'[^a-z0-9]+','',(s or '').lower()) or 'unknown'

def text(item): return f"{field(item,'title')} {field(item,'description')} {field(item,'whyMatters')}"

def parse(path):
    return list(ET.parse(path).getroot().findall('.//item'))

def max_streak(items):
    best=(0,'',0); cur=''; start=0; n=0
    for idx,i in enumerate(items):
        s=source_id(field(i,'source'))
        if s==cur: n+=1
        else: cur=s; start=idx; n=1
        if n>best[0]: best=(n,field(i,'source'),start)
    return best

def fuzzy_dupes(items):
    out=[]
    nts=[norm_title(field(i,'title')) for i in items]
    for a in range(len(items)):
        if len(nts[a])<24: continue
        wa=set(nts[a].split())
        for b in range(a+1,len(items)):
            if len(nts[b])<24: continue
            wb=set(nts[b].split())
            overlap=len(wa&wb)/max(1,min(len(wa),len(wb)))
            if overlap<0.58: continue
            ratio=SequenceMatcher(None,nts[a],nts[b]).ratio()
            if ratio>=0.80 or overlap>=0.78:
                out.append({'a':field(items[a],'title'),'b':field(items[b],'title'),'sourceA':field(items[a],'source'),'sourceB':field(items[b],'source'),'ratio':round(ratio,2),'overlap':round(overlap,2)})
    return out[:20]

def heuristic_mismatch(i,cat):
    t=text(i); title=field(i,'title'); reasons=[]
    # Catch obvious specialist leakage independently of the production classifier.
    if cat in {'world','us','presidential','federal','nm','local','region'}:
        if SPORT_RE.search(title) and not (cat=='local' and LOCAL_RE.search(title)): reasons.append('sports-looking headline in civic/geography tab')
        if GAMING_RE.search(title): reasons.append('gaming-looking headline outside Gaming')
        if TECH_RE.search(title) and not any(r.search(title) for r in (PRES_RE,FED_RE,NM_RE,LOCAL_RE)): reasons.append('technology/product-looking headline outside Technology')
    if cat=='technology' and GAMING_RE.search(title) and not TECH_RE.search(title): reasons.append('gaming-only headline in Technology')
    if cat=='gaming' and TECH_RE.search(title) and not GAMING_RE.search(title): reasons.append('hardware/technology-only headline in Gaming')
    if cat=='military' and not MIL_RE.search(t): reasons.append('weak/no military anchor')
    if cat=='presidential' and not PRES_RE.search(t): reasons.append('weak/no presidential anchor')
    if cat=='federal' and not FED_RE.search(t): reasons.append('weak/no federal anchor')
    if cat=='nm' and not NM_RE.search(t) and not field(i,'state').lower()=='new mexico': reasons.append('weak/no New Mexico anchor')
    if cat=='local' and not field(i,'marketId') and not LOCAL_RE.search(t): reasons.append('no local market metadata or Four Corners anchor')
    if cat=='region' and not (field(i,'region') and field(i,'state')): reasons.append('missing region/state inventory metadata')
    if cat=='nfl' and not qualifies(i,'nfl'): reasons.append('fails NFL semantic gate')
    if cat=='technology' and not qualifies(i,'technology'): reasons.append('fails Technology semantic gate')
    if cat=='gaming' and not qualifies(i,'gaming'): reasons.append('fails Gaming semantic gate')
    if cat=='world' and not qualifies(i,'world'): reasons.append('fails World semantic gate')
    if cat=='us' and not qualifies(i,'us'): reasons.append('fails US semantic gate')
    if cat=='legislation' and not qualifies(i,'legislation'): reasons.append('fails Legislation semantic gate')
    return reasons

def analyze(items):
    by=defaultdict(list)
    for i in items: by[field(i,'category').lower()].append(i)
    result={}
    for cat in TABS:
        arr=by.get(cat,[]); src=Counter(field(i,'source') or 'Unknown' for i in arr); streak=max_streak(arr)
        exact_titles=defaultdict(list); exact_urls=defaultdict(list)
        for i in arr:
            exact_titles[norm_title(field(i,'title'))].append(i)
            u=(norm_legislation_url(field(i,'link')) if cat=='legislation' else norm_url(field(i,'link')))
            if u: exact_urls[u].append(i)
        exact=[]
        for k,v in exact_titles.items():
            if k and len(v)>1: exact.append([field(x,'title') for x in v])
        for k,v in exact_urls.items():
            if len(v)>1 and not any(set(field(x,'title') for x in v)==set(g) for g in exact): exact.append([field(x,'title') for x in v])
        mism=[]
        for idx,i in enumerate(arr):
            reasons=[]
            if cat in OWNERSHIP:
                try:
                    target,_,scores=safe_best_tab(i)
                    if target and target!=cat: reasons.append(f'production classifier prefers {target}')
                except Exception as e: reasons.append('classifier-error')
            if cat=='entertainment' and not ENT_RE.search(text(i)): reasons.append('weak/no entertainment anchor')
            reasons += heuristic_mismatch(i,cat)
            if reasons:
                mism.append({'position':idx+1,'title':field(i,'title'),'source':field(i,'source'),'reasons':sorted(set(reasons))})
        first10=[field(i,'source') for i in arr[:10]]
        result[cat]={
            'count':len(arr),'uniqueSources':len(src),'topSources':src.most_common(6),
            'topSourceShare':round((src.most_common(1)[0][1]/len(arr)*100),1) if arr else 0,
            'first10Sources':first10,'first10DistinctSources':len(set(source_id(x) for x in first10)),
            'maxConsecutiveSameSource':{'count':streak[0],'source':streak[1],'startPosition':streak[2]+1 if streak[0] else 0},
            'exactDuplicateGroups':exact[:15],'fuzzyDuplicatePairs':fuzzy_dupes(arr),
            'mismatchCandidates':mism[:40],'mismatchCount':len(mism),
        }
    # Exact cross-tab repeats among ownership tabs.
    title_places=defaultdict(list); url_places=defaultdict(list)
    for cat in OWNERSHIP:
        for i in by.get(cat,[]):
            nt=norm_title(field(i,'title'))
            u=(norm_legislation_url(field(i,'link')) if cat=='legislation' else norm_url(field(i,'link')))
            if nt: title_places[nt].append((cat,field(i,'title'),field(i,'source')))
            if u: url_places[u].append((cat,field(i,'title'),field(i,'source')))
    cross=[]; seen=set()
    for groups in (title_places,url_places):
        for _,v in groups.items():
            cats={x[0] for x in v}
            if len(cats)>1:
                key=tuple(sorted((x[0],norm_title(x[1])) for x in v))
                if key not in seen: cross.append(v); seen.add(key)
    return result,cross[:50]

def render(old,new,cross_old,cross_new):
    lines=['# V5.1 vs V5.2 Content Audit','', 'Automated semantic + sequence audit. Mismatch candidates are review flags, not automatic deletions.','',
           '| Tab | V5.1 count | V5.2 count | V5.1 mismatches | V5.2 mismatches | V5.1 max source streak | V5.2 max source streak | V5.2 top source |',
           '|---|---:|---:|---:|---:|---|---|---|']
    for cat in TABS:
        a=old[cat]; b=new[cat]; sa=a['maxConsecutiveSameSource']; sb=b['maxConsecutiveSameSource']; ts=b['topSources'][0] if b['topSources'] else ('',0)
        lines.append(f"| {cat} | {a['count']} | {b['count']} | {a['mismatchCount']} | {b['mismatchCount']} | {sa['count']}× {sa['source']} | {sb['count']}× {sb['source']} | {ts[0]} {ts[1]} ({b['topSourceShare']}%) |")
    lines += ['',f"Exact cross-tab repeat groups: V5.1={len(cross_old)}, V5.2={len(cross_new)}",'']
    for cat in TABS:
        b=new[cat]; a=old[cat]
        lines += [f'## {cat}',f"V5.1: {a['count']} items, {a['uniqueSources']} sources, streak {a['maxConsecutiveSameSource']['count']}× {a['maxConsecutiveSameSource']['source']}; V5.2: {b['count']} items, {b['uniqueSources']} sources, streak {b['maxConsecutiveSameSource']['count']}× {b['maxConsecutiveSameSource']['source']}.",
                  f"V5.2 top sources: {', '.join(f'{s} ({n})' for s,n in b['topSources'])}",
                  f"V5.2 duplicate flags: exact={len(b['exactDuplicateGroups'])}, fuzzy={len(b['fuzzyDuplicatePairs'])}; mismatch candidates={b['mismatchCount']}." ]
        if b['mismatchCandidates']:
            lines.append('Mismatch candidates:')
            for x in b['mismatchCandidates'][:12]: lines.append(f"- #{x['position']} — {x['source']} — {x['title']} — {'; '.join(x['reasons'])}")
        if b['fuzzyDuplicatePairs']:
            lines.append('Likely duplicate candidates:')
            for x in b['fuzzyDuplicatePairs'][:8]: lines.append(f"- {x['sourceA']}: {x['a']}  ⇄  {x['sourceB']}: {x['b']} (overlap {x['overlap']})")
        lines.append('')
    if cross_new:
        lines += ['## V5.2 exact cross-tab repeats']
        for g in cross_new[:20]: lines.append('- ' + ' | '.join(f"{c}: {s}: {t}" for c,t,s in g))
    return '\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser(); p.add_argument('--baseline',required=True); p.add_argument('--candidate',default='News'); p.add_argument('--json',default='v52-content-audit.json'); p.add_argument('--md',default='v52-content-audit.md'); a=p.parse_args()
    old_items=parse(a.baseline); new_items=parse(a.candidate)
    old,cross_old=analyze(old_items); new,cross_new=analyze(new_items)
    payload={'baseline':old,'v52':new,'baselineCrossTabRepeats':cross_old,'v52CrossTabRepeats':cross_new}
    Path(a.json).write_text(json.dumps(payload,indent=2),encoding='utf-8')
    md=render(old,new,cross_old,cross_new); Path(a.md).write_text(md,encoding='utf-8'); print(md)

if __name__=='__main__': main()
