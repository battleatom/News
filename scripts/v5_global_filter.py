#!/usr/bin/env python3
"""Fresh V5 final global ownership filter.
Pipeline: per-tab qualification -> within-tab event dedupe -> cross-tab event ownership.
Top Stories is preserved as a ranking surface and may intentionally mirror a canonical story.
"""
from __future__ import annotations
import argparse,json,shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from v5_tab_filters import field,tab_filter_decision,best_tab,RULES,RANKING_SURFACES,SPECIAL_SURFACES
from v5_tab_dedupe import dedupe_within_tabs,cross_tab_clusters,event_similarity

def set_category(item:ET.Element,category:str)->None:
    el=item.find("category")
    if el is None: el=ET.SubElement(item,"category")
    el.text=category

def ownership_score(item:ET.Element,target:str)->tuple:
    _,_,scores=best_tab(item)
    margin=scores.get(target,0.0)-RULES[target].threshold if target in RULES else -999
    return (margin,RULES.get(target,RULES["world"]).specificity,scores.get(target,0.0),len(field(item,"description")))

def apply_pipeline(input_path:str,output_path:str|None=None,report_path:str|None=None)->dict:
    tree=ET.parse(input_path); channel=tree.getroot().find("channel")
    if channel is None: raise SystemExit("RSS channel missing")
    original=list(channel.findall("item")); baseline_counts=Counter(field(i,"category").lower() for i in original)
    routed=[]; route_changes=[]; unresolved=[]
    for item in original:
        current=field(item,"category").lower(); decision=tab_filter_decision(item)
        if current=="top": routed.append(item); continue
        target=decision["target"]
        if decision["action"]=="reroute" and target and target!=current:
            if target in SPECIAL_SURFACES and current not in SPECIAL_SURFACES: target,_,_=best_tab(item,include_special=False)
            if target and target!=current:
                set_category(item,target); route_changes.append({"title":field(item,"title"),"from":current,"to":target,"reason":decision["reason"]})
        elif decision["action"]=="review": unresolved.append({"title":field(item,"title"),"category":current,"reason":decision["reason"]})
        routed.append(item)
    routed,within_removed=dedupe_within_tabs(routed)
    clusters=cross_tab_clusters(routed); remove_ids=set(); ownership_changes=[]
    for cluster in clusters:
        candidates=[]
        for item in cluster:
            current=field(item,"category").lower(); target,_,_=best_tab(item,include_special=current in SPECIAL_SURFACES)
            if target in SPECIAL_SURFACES and current not in SPECIAL_SURFACES: target,_,_=best_tab(item,include_special=False)
            candidates.append((item,target,ownership_score(item,target)))
        canonical_item,canonical_tab,_=max(candidates,key=lambda x:x[2])
        if field(canonical_item,"category").lower()!=canonical_tab:
            old=field(canonical_item,"category").lower(); set_category(canonical_item,canonical_tab)
            ownership_changes.append({"title":field(canonical_item,"title"),"from":old,"to":canonical_tab,"reason":"cross-tab-owner"})
        for item,target,_ in candidates:
            if item is canonical_item: continue
            remove_ids.add(id(item)); ownership_changes.append({"title":field(item,"title"),"from":field(item,"category").lower(),"to":canonical_tab,"reason":"duplicate-event-removed","similarity":event_similarity(item,canonical_item),"canonicalTitle":field(canonical_item,"title")})
    final_items=[i for i in routed if id(i) not in remove_ids]; final_counts=Counter(field(i,"category").lower() for i in final_items)
    if output_path:
        for item in list(channel.findall("item")): channel.remove(item)
        for item in final_items: channel.append(item)
        tree.write(output_path,encoding="utf-8",xml_declaration=True)
    report={"mode":"v5-fresh-tab-filter-shadow","inputArticles":len(original),"outputArticles":len(final_items),"baselineCounts":dict(baseline_counts),"finalCounts":dict(final_counts),"rerouted":len(route_changes),"withinTabDuplicatesRemoved":len(within_removed),"crossTabDuplicateEvents":len(clusters),"crossTabDuplicatesRemoved":len(remove_ids),"unresolved":len(unresolved),"routeChanges":route_changes[:200],"withinTabDuplicateExamples":within_removed[:100],"ownershipChanges":ownership_changes[:200],"unresolvedExamples":unresolved[:100]}
    if report_path: Path(report_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--input",default="News"); p.add_argument("--output"); p.add_argument("--report",default="v5-filter-shadow-report.json"); p.add_argument("--apply",action="store_true"); args=p.parse_args()
    output=args.output
    if args.apply and not output:
        shutil.copyfile(args.input,args.input+".pre-v5-filter"); output=args.input
    report=apply_pipeline(args.input,output,args.report)
    print(json.dumps({k:v for k,v in report.items() if k not in {"routeChanges","withinTabDuplicateExamples","ownershipChanges","unresolvedExamples"}},indent=2))
if __name__=="__main__": main()
