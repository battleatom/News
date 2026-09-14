#!/usr/bin/env python3
"""Fresh V5 authoritative routing, dedupe, and global ownership filter."""
from __future__ import annotations
import argparse,json,re,shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from v5_tab_filters import field,tab_filter_decision,best_tab,RULES,RANKING_SURFACES,EDITORIAL_OVERLAYS,LEGACY_CATEGORY_MAP,qualifies
from v5_tab_dedupe import dedupe_within_tabs,cross_tab_clusters,event_similarity

PROTECTED_CATEGORIES={"boxoffice","entertainment"}
BROAD_TABS={"world","us"}
GEO_TABS={"local","nm","region"}
SPORT_WORDS=re.compile(r"\b(football|basketball|baseball|hockey|soccer|volleyball|softball|golf|tennis|rockies|byu|utah tech|tigers|stakes)\b",re.I)
PRESIDENTIAL_CONTEXT=re.compile(r"\b(president trump|donald trump|trump administration|white house (says|announces|orders|proposes|officials|weighs)|executive order|press secretary)\b",re.I)
PRESIDENTIAL_HEADLINE=re.compile(r"^(?:(?:the latest|fact check):\s*)?(?:president\s+)?trump\b|^(?:five big takeaways from|what to know about)\s+trump(?:'s)?\b",re.I)
MILITARY_TITLE_ANCHOR=re.compile(r"\b(pentagon|military|army|navy|air force|marines?|troops?|missiles?|airstrikes?|drone(?: strike| warfare)?|warships?|combat|battlefield|invasion|ceasefire|defense department|centcom|fighter jets?|f-?35|apache|saildrone|usv|munitions?|weapon systems?|hegseth|anduril|warfighters?|houthis?)\b",re.I)
FEDERAL_HEADLINE=re.compile(r"\b(federal appeals court|federal debt|senate hearing)\b",re.I)
GAMING_HEADLINE=re.compile(r"\b(playstation|xbox|nintendo|steam|pc gamer|video game|gaming|game studio|esports|dlc)\b",re.I)
GENERIC_NOISE_HEADLINE=re.compile(r"^(coming sunday and monday|coming this week|latest headlines|news roundup)\b",re.I)
GEO_TITLE={
    "local":re.compile(r"\b(farmington|san juan county|aztec|bloomfield|kirtland|shiprock|four corners|durango|la plata county|cortez|montezuma county|navajo nation)\b",re.I),
    "nm":re.compile(r"\b(new mexico|new mexicans?|santa fe|albuquerque|las cruces|rio rancho|nmdot)\b",re.I),
    "region":re.compile(r"\b(arizona|colorado|utah|flagstaff|phoenix|denver|salt lake city|southern colorado|northern arizona)\b",re.I),
}

def set_category(item:ET.Element,cat:str)->None:
    e=item.find("category")
    if e is None:e=ET.SubElement(item,"category")
    e.text=cat

def clean_headline(item:ET.Element)->str:
    t=field(item,"title")
    return t.rsplit(" - ",1)[0] if " - " in t else t

def candidate_tabs(scores:dict,excluded:set[str]|None=None)->list[str]:
    excluded=set(excluded or ())|PROTECTED_CATEGORIES|RANKING_SURFACES|EDITORIAL_OVERLAYS
    c=[t for t,s in scores.items() if t in RULES and t not in excluded and s>=RULES[t].threshold]
    c.sort(key=lambda t:(RULES[t].specificity,scores[t]-RULES[t].threshold,scores[t]),reverse=True)
    return c

def direct_presidential_story(item:ET.Element)->bool:
    return bool(PRESIDENTIAL_HEADLINE.search(clean_headline(item)))

def military_headline_anchor(item:ET.Element)->bool:
    title=re.sub(r"\bair force one\b","",clean_headline(item),flags=re.I)
    return bool(MILITARY_TITLE_ANCHOR.search(title))

def target_is_contextually_valid(item:ET.Element,current:str,target:str)->bool:
    title=clean_headline(item)
    if target=="military" and current!="military" and not military_headline_anchor(item):return False
    if target=="region" and SPORT_WORDS.search(title) and current!="region":return False
    if target in GEO_TABS and current not in GEO_TABS and not GEO_TITLE[target].search(title):return False
    if target=="presidential" and current!="presidential" and not (PRESIDENTIAL_CONTEXT.search(title) or direct_presidential_story(item)):return False
    return True

def resolve_target(item:ET.Element,current:str,target:str|None,scores:dict)->str|None:
    title=clean_headline(item)
    # Explicit federal institutional language outranks broad U.S./World routing.
    if FEDERAL_HEADLINE.search(title) and current in {"federal","us","world","presidential"}:return "federal"
    # Direct Trump headline stories are Presidential unless an explicitly structured Legislation/Federal
    # event is the stronger subject. This does not apply to incidental Trump mentions later in a headline.
    if direct_presidential_story(item) and current in {"presidential","world","us","federal"}:
        for specific in ("legislation","federal"):
            if scores.get(specific,0)>=RULES[specific].threshold+5:return specific
        return "presidential"
    excluded=set()
    if target in PROTECTED_CATEGORIES:excluded.add(target)
    if target and not target_is_contextually_valid(item,current,target):excluded.add(target)
    if current in GEO_TABS and qualifies(item,current) and target in BROAD_TABS:return current
    if current=="military" and target=="world" and qualifies(item,"military"):return current
    # A story already collected as Gaming with an explicit gaming headline/source signal should not
    # be lost to a generic U.S./World geography mention.
    if current=="gaming" and target in BROAD_TABS and GAMING_HEADLINE.search(field(item,"title")):return current
    if target and target not in excluded:return target
    for fallback in candidate_tabs(scores,excluded):
        if target_is_contextually_valid(item,current,fallback):return fallback
    return None

def safe_best_tab(item:ET.Element)->tuple:
    current=field(item,"category").lower();target,score,scores=best_tab(item,include_underreported=(current=="underreported"));target=resolve_target(item,current,target,scores)
    return (target,scores.get(target,0) if target else 0,scores)

def ownership_score(item:ET.Element,target:str)->tuple:
    _,_,scores=safe_best_tab(item);return (scores.get(target,0)-RULES[target].threshold,RULES[target].specificity,scores.get(target,0),len(field(item,"description")))

def apply_pipeline(input_path:str,output_path:str|None=None,report_path:str|None=None)->dict:
    tree=ET.parse(input_path);channel=tree.getroot().find("channel")
    if channel is None:raise SystemExit("RSS channel missing")
    original=list(channel.findall("item"));base=Counter(field(i,"category").lower() for i in original)
    routed=[];changes=[];rejected=[]
    for item in original:
        raw=field(item,"category").lower()
        if raw in PROTECTED_CATEGORIES:routed.append(item);continue
        current=LEGACY_CATEGORY_MAP.get(raw,raw)
        if current!=raw:set_category(item,current)
        # Catch publisher promos/generic pages before category scoring can turn their source name
        # into a false geography match.
        if GENERIC_NOISE_HEADLINE.search(clean_headline(item)):
            rejected.append({"title":field(item,"title"),"from":current,"reason":"global-generic-page"});continue
        d=tab_filter_decision(item)
        if d["action"]=="reject" and d["reason"]=="no-qualified-tab" and current=="presidential" and direct_presidential_story(item):
            d={**d,"action":"keep","target":"presidential","reason":"presidential-headline-preserved"}
        if d["action"]=="reject":rejected.append({"title":field(item,"title"),"from":current,"reason":d["reason"]});continue
        target=resolve_target(item,current,d.get("target"),d["scores"])
        if target is None:rejected.append({"title":field(item,"title"),"from":current,"reason":"no-valid-qualified-target"});continue
        if target!=d.get("target"):d={**d,"action":"keep" if target==current else "reroute","target":target,"reason":"contextual-target:"+target}
        if d["action"]=="reroute" and d["target"]!=current:
            set_category(item,d["target"]);changes.append({"title":field(item,"title"),"from":current,"to":d["target"],"reason":d["reason"]})
        routed.append(item)
    routed,within=dedupe_within_tabs(routed)
    clusters=cross_tab_clusters(routed);remove=set();ownership=[]
    for cluster in clusters:
        candidates=[]
        for item in cluster:
            current=field(item,"category").lower()
            if current in PROTECTED_CATEGORIES:continue
            target,_,_=safe_best_tab(item)
            if target is None:continue
            candidates.append((item,target,ownership_score(item,target)))
        if len(candidates)<2:continue
        canonical,target,_=max(candidates,key=lambda x:x[2])
        if field(canonical,"category").lower()!=target:
            old=field(canonical,"category").lower();set_category(canonical,target);ownership.append({"title":field(canonical,"title"),"from":old,"to":target,"reason":"cross-tab-owner"})
        for item,_,_ in candidates:
            if item is canonical:continue
            remove.add(id(item));ownership.append({"title":field(item,"title"),"from":field(item,"category").lower(),"to":target,"reason":"duplicate-event-removed","similarity":event_similarity(item,canonical),"canonicalTitle":field(canonical,"title")})
    final=[i for i in routed if id(i) not in remove];final_counts=Counter(field(i,"category").lower() for i in final)
    if output_path:
        for i in list(channel.findall("item")):channel.remove(i)
        for i in final:channel.append(i)
        tree.write(output_path,encoding="utf-8",xml_declaration=True)
    report={"mode":"v5-fresh-authoritative-shadow","inputArticles":len(original),"outputArticles":len(final),"baselineCounts":dict(base),"finalCounts":dict(final_counts),"rerouted":len(changes),"rejectedNoQualifiedTab":len(rejected),"withinTabDuplicatesRemoved":len(within),"crossTabDuplicateEvents":len(clusters),"crossTabDuplicatesRemoved":len(remove),"protectedCategories":sorted(PROTECTED_CATEGORIES),"routeChanges":changes[:250],"rejectedExamples":rejected[:250],"withinTabDuplicateExamples":within[:150],"ownershipChanges":ownership[:250]}
    if report_path:Path(report_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",default="News");p.add_argument("--output");p.add_argument("--report",default="v5-filter-shadow-report.json");p.add_argument("--apply",action="store_true");a=p.parse_args();out=a.output
    if a.apply and not out:shutil.copyfile(a.input,a.input+".pre-v5-filter");out=a.input
    r=apply_pipeline(a.input,out,a.report);print(json.dumps({k:v for k,v in r.items() if not isinstance(v,list)},indent=2))
if __name__=="__main__":main()
