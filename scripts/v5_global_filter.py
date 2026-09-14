#!/usr/bin/env python3
"""Fresh V5 authoritative routing, dedupe, and global ownership filter."""
from __future__ import annotations
import argparse,json,shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from v5_tab_filters import field,tab_filter_decision,best_tab,RULES,RANKING_SURFACES,LEGACY_CATEGORY_MAP,qualifies
from v5_tab_dedupe import dedupe_within_tabs,cross_tab_clusters,event_similarity

def set_category(item:ET.Element,cat:str)->None:
    e=item.find("category")
    if e is None:e=ET.SubElement(item,"category")
    e.text=cat

def ownership_score(item:ET.Element,target:str)->tuple:
    _,_,scores=best_tab(item,include_underreported=(field(item,"category").lower()=="underreported"))
    return (scores.get(target,0)-RULES[target].threshold,RULES[target].specificity,scores.get(target,0),len(field(item,"description")))
def apply_pipeline(input_path:str,output_path:str|None=None,report_path:str|None=None)->dict:
    tree=ET.parse(input_path);channel=tree.getroot().find("channel")
    if channel is None:raise SystemExit("RSS channel missing")
    original=list(channel.findall("item"));base=Counter(LEGACY_CATEGORY_MAP.get(field(i,"category").lower(),field(i,"category").lower()) for i in original)
    routed=[];changes=[];rejected=[]
    for item in original:
        raw=field(item,"category").lower();current=LEGACY_CATEGORY_MAP.get(raw,raw)
        if current!=raw:set_category(item,current)
        d=tab_filter_decision(item)
        if d["action"]=="reject":rejected.append({"title":field(item,"title"),"from":current,"reason":d["reason"]});continue
        if d["action"]=="reroute" and d["target"]!=current:
            set_category(item,d["target"]);changes.append({"title":field(item,"title"),"from":current,"to":d["target"],"reason":d["reason"]})
        routed.append(item)
    routed,within=dedupe_within_tabs(routed)
    clusters=cross_tab_clusters(routed);remove=set();ownership=[]
    for cluster in clusters:
        candidates=[]
        for item in cluster:
            current=field(item,"category").lower();target,_,_=best_tab(item,include_underreported=(current=="underreported"))
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
    report={"mode":"v5-fresh-authoritative-shadow","inputArticles":len(original),"outputArticles":len(final),"baselineCounts":dict(base),"finalCounts":dict(final_counts),"rerouted":len(changes),"rejectedNoQualifiedTab":len(rejected),"withinTabDuplicatesRemoved":len(within),"crossTabDuplicateEvents":len(clusters),"crossTabDuplicatesRemoved":len(remove),"routeChanges":changes[:250],"rejectedExamples":rejected[:250],"withinTabDuplicateExamples":within[:150],"ownershipChanges":ownership[:250]}
    if report_path:Path(report_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",default="News");p.add_argument("--output");p.add_argument("--report",default="v5-filter-shadow-report.json");p.add_argument("--apply",action="store_true");a=p.parse_args();out=a.output
    if a.apply and not out:shutil.copyfile(a.input,a.input+".pre-v5-filter");out=a.input
    r=apply_pipeline(a.input,out,a.report);print(json.dumps({k:v for k,v in r.items() if not isinstance(v,list)},indent=2))
if __name__=="__main__":main()
