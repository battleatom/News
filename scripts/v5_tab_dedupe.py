#!/usr/bin/env python3
"""Fresh V5 event dedupe built on per-tab filter semantics."""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from collections import defaultdict,Counter
from difflib import SequenceMatcher
from typing import Dict,List,Tuple
from v5_tab_filters import field,content_tokens,RULES,best_tab,RANKING_SURFACES

def norm_title(item:ET.Element)->str:
    title=field(item,"title").lower(); title=re.sub(r"\s+-\s+[^-]{2,40}$","",title)
    return re.sub(r"[^a-z0-9]+"," ",title).strip()

def canonical_url(item:ET.Element)->str:
    u=field(item,"resolvedPublisherUrl") or field(item,"link")
    return re.sub(r"[?#].*$","",u.strip().lower()).rstrip("/")

def _features(item:ET.Element)->dict:
    toks=content_tokens(item); title=norm_title(item); title_tokens={t for t in title.split() if len(t)>=4}
    anchors={x for x in toks if any(c.isdigit() for c in x) or len(x)>=8}
    return {"title":title,"url":canonical_url(item),"tokens":toks,"title_tokens":title_tokens,"anchors":anchors,"tab":field(item,"category").lower()}

def event_similarity(a:ET.Element,b:ET.Element,fa:dict|None=None,fb:dict|None=None)->float:
    fa=fa or _features(a); fb=fb or _features(b)
    if fa["url"] and fb["url"] and fa["url"]==fb["url"]:return 1.0
    if fa["title"] and fb["title"] and fa["title"]==fb["title"]:return 1.0
    title_ratio=SequenceMatcher(None,fa["title"],fb["title"]).ratio() if fa["title"] and fb["title"] else 0.0
    A,B=fa["tokens"],fb["tokens"]; jac=len(A&B)/max(1,len(A|B)); score=.58*title_ratio+.42*jac
    if len(fa["anchors"]&fb["anchors"])>=2:score+=.08
    return min(1.0,round(score,4))

def same_event(a:ET.Element,b:ET.Element,fa:dict|None=None,fb:dict|None=None)->bool:
    fa=fa or _features(a); fb=fb or _features(b)
    if fa["url"] and fb["url"] and fa["url"]==fb["url"]:return True
    shared_title=len(fa["title_tokens"]&fb["title_tokens"]); shared_all=len(fa["tokens"]&fb["tokens"])
    if shared_title<2 and shared_all<3:return False
    s=event_similarity(a,b,fa,fb)
    if s>=.78:return True
    if s<.70:return False
    wa,_,_=best_tab(a); wb,_,_=best_tab(b)
    return wa==wb and RULES.get(wa,RULES["world"]).specificity>=8

def _candidate_pairs(group:List[ET.Element],cross_tab_only:bool=False):
    feats=[_features(x) for x in group]; inv=defaultdict(list); pair_hits=Counter(); url_pairs=set()
    for idx,f in enumerate(feats):
        keys=(f["title_tokens"]|f["anchors"])
        for tok in keys:
            for prior in inv[tok]:
                if cross_tab_only and feats[prior]["tab"]==f["tab"]:continue
                pair_hits[(prior,idx)]+=1
            inv[tok].append(idx)
    by_url=defaultdict(list)
    for idx,f in enumerate(feats):
        if not f["url"] : continue
        for prior in by_url[f["url"]]:
            if not cross_tab_only or feats[prior]["tab"]!=f["tab"]:url_pairs.add((prior,idx))
        by_url[f["url"]].append(idx)
    pairs=set(url_pairs)
    pairs.update(pair for pair,hits in pair_hits.items() if hits>=2)
    return feats,sorted(pairs)

def dedupe_within_tabs(items:List[ET.Element])->Tuple[List[ET.Element],List[dict]]:
    kept=[];removed=[];by_tab:Dict[str,List[ET.Element]]=defaultdict(list)
    for item in items:by_tab[field(item,"category").lower()].append(item)
    for tab,group in by_tab.items():
        feats,pairs=_candidate_pairs(group); duplicate_of={}
        for i,j in pairs:
            if j in duplicate_of:continue
            root=i
            while root in duplicate_of:root=duplicate_of[root]
            if same_event(group[root],group[j],feats[root],feats[j]):duplicate_of[j]=root
        for idx,item in enumerate(group):
            if idx not in duplicate_of:kept.append(item);continue
            root=duplicate_of[idx]
            removed.append({"scope":"within-tab","tab":tab,"removed":field(item,"title"),"kept":field(group[root],"title"),"similarity":event_similarity(item,group[root],feats[idx],feats[root])})
    return kept,removed

def cross_tab_clusters(items:List[ET.Element])->List[List[ET.Element]]:
    normal=[i for i in items if field(i,"category").lower() not in RANKING_SURFACES]
    feats,pairs=_candidate_pairs(normal,cross_tab_only=True); parent=list(range(len(normal)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb:parent[rb]=ra
    for i,j in pairs:
        if same_event(normal[i],normal[j],feats[i],feats[j]):union(i,j)
    groups=defaultdict(list)
    for i,item in enumerate(normal):groups[find(i)].append(item)
    return [g for g in groups.values() if len(g)>1 and len({field(x,'category').lower() for x in g})>1]
