#!/usr/bin/env python3
"""Fresh V5 event dedupe built on per-tab filter semantics."""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict,List,Tuple
from v5_tab_filters import field,content_tokens,RULES,best_tab,RANKING_SURFACES

def norm_title(item:ET.Element)->str:
    title=field(item,"title").lower(); title=re.sub(r"\s+-\s+[^-]{2,40}$","",title)
    return re.sub(r"[^a-z0-9]+"," ",title).strip()

def canonical_url(item:ET.Element)->str:
    u=field(item,"resolvedPublisherUrl") or field(item,"link")
    return re.sub(r"[?#].*$","",u.strip().lower()).rstrip("/")

def event_similarity(a:ET.Element,b:ET.Element)->float:
    ua,ub=canonical_url(a),canonical_url(b)
    if ua and ub and ua==ub:return 1.0
    ta,tb=norm_title(a),norm_title(b)
    if ta and tb and ta==tb:return 1.0
    title_ratio=SequenceMatcher(None,ta,tb).ratio() if ta and tb else 0.0
    A,B=content_tokens(a),content_tokens(b); jac=len(A&B)/max(1,len(A|B))
    anchors_a={x for x in A if any(c.isdigit() for c in x) or len(x)>=8}; anchors_b={x for x in B if any(c.isdigit() for c in x) or len(x)>=8}
    score=.56*title_ratio+.44*jac
    if len(anchors_a&anchors_b)>=2: score+=.08
    return min(1.0,round(score,4))

def same_event(a:ET.Element,b:ET.Element)->bool:
    s=event_similarity(a,b)
    if s>=.78:return True
    wa,_,_=best_tab(a); wb,_,_=best_tab(b)
    return wa==wb and RULES.get(wa,RULES["world"]).specificity>=8 and s>=.70

def dedupe_within_tabs(items:List[ET.Element])->Tuple[List[ET.Element],List[dict]]:
    kept=[]; removed=[]; by_tab:Dict[str,List[ET.Element]]=defaultdict(list)
    for item in items: by_tab[field(item,"category").lower()].append(item)
    for tab,group in by_tab.items():
        tab_kept=[]
        for item in group:
            match=next((x for x in tab_kept if same_event(item,x)),None)
            if match is None: tab_kept.append(item)
            else: removed.append({"scope":"within-tab","tab":tab,"removed":field(item,"title"),"kept":field(match,"title"),"similarity":event_similarity(item,match)})
        kept.extend(tab_kept)
    return kept,removed

def cross_tab_clusters(items:List[ET.Element])->List[List[ET.Element]]:
    normal=[i for i in items if field(i,"category").lower() not in RANKING_SURFACES]; clusters=[]; used=set()
    for idx,item in enumerate(normal):
        if idx in used:continue
        cluster=[item]; used.add(idx)
        for j in range(idx+1,len(normal)):
            if j in used:continue
            other=normal[j]
            if field(other,"category").lower()==field(item,"category").lower():continue
            if any(same_event(other,member) for member in cluster): cluster.append(other); used.add(j)
        if len(cluster)>1:clusters.append(cluster)
    return clusters
