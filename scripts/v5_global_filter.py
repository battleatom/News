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
SPORT_WORDS=re.compile(r"\b(football|basketball|baseball|hockey|soccer|volleyball|softball|golf|tennis)\b",re.I)
PRESIDENTIAL_CONTEXT=re.compile(r"\b(trump|president trump|white house (says|announces|orders|proposes|officials)|trump administration|executive order|press secretary)\b",re.I)

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

def best_unprotected_from_scores(scores:dict,excluded:set[str]|None=None)->str|None:
    c=candidate_tabs(scores,excluded);return c[0] if c else None

def target_is_contextually_valid(item:ET.Element,current:str,target:str)->bool:
    title=clean_headline(item)
    if target=="region" and SPORT_WORDS.search(title) and current!="region":return False
    if target=="presidential" and not PRESIDENTIAL_CONTEXT.search(title):return False
    return True

def resolve_target(item:ET.Element,current:str,target:str|None,scores:dict)->str|None:
    excluded=set()
    if target in PROTECTED_CATEGORIES:excluded.add(target)
    if target and not target_is_contextually_valid(item,current,target):excluded.add(target)
    if current in GEO_TABS and qualifies(item,current) and target in BROAD_TABS:return current
    if current=="military" and target=="world" and qualifies(item,"military"):return current
    if current=="presidential" and target in BROAD_TABS and qualifies(item,"presidential") and PRESIDENTIAL_CONTEXT.search(clean_headline(item)):return current
    if current=="gaming" and target in BROAD_TABS and qualifies(item,"gaming") and re.search(r"\b(game|gaming|playstation|xbox|nintendo|steam|pc gamer|console|dlc|esports)\b",field(item,"title"),re.I):return current
    if target and target not in excluded:return target
    return best_unprotected_from_scores(scores,excluded)

def safe_best_tab(item:ET.Element)->tuple:
    current=field(item,"category").lower()
    target,score,scores=best_tab(item,include_underreported=(current=="underreported"))
    target=resolve_target(item,current,target,scores)
    return (target,scores.get(target,0) if target else 0,scores)

def ownership_score(item:ET.Element,target:str)->tuple:
    _,_,scores=safe_best_tab(item)
    return (scores.get(target,0)-RULES[target].threshold,RULES[target].specificity,scores.get(target,0),len(field(item,"description")))

def apply_pipeline(input_path:str,output_path:str|None=None,report_path:str|None=None)->dict:
    tree=ET.parse(input_path);channel=tree.getroot().find("channel")
    if channel is None:raise SystemExit("RSS channel missing")
    original=list(channel.findall("item"));base=Counter(field(i,"category").lower() for i in original)
    routed=[];changes=[];rejected=[]
    for item in original:
        raw=field(item,"category").lower()
        if raw in PROTECTED_CATEGORIES:
            routed.append(item);continue
        current=LEGACY_CATEGORY_MAP.get(raw,raw)
        if current!=raw:set_category(item,current)
        d=tab_filter_decision(item)
        # A tab filter rejection is authoritative. Never resurrect noise/out-of-area content
        # merely because a weaker fallback category happens to score.
        if d["action"]=="reject":
            rejected.append({"title":field(item,"title"),"from":current,"reason":d["reason"]});continue
        target=resolve_target(item,current,d.get("target"),d["scores"])
        if target is None:
            rejected.append({"title":field(item,"title"),"from":current,"reason":"no-valid-qualified-target"});continue
        if target!=d.get("target"):
            d={**d,"action":"keep" if target==current else "reroute","target":target,"reason":"contextual-target:"+target}
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
