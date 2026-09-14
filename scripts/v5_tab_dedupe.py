#!/usr/bin/env python3
"""Fresh V5 tab-aware event dedupe. Avoids publisher-home and template false matches."""
from __future__ import annotations
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict,Counter
from difflib import SequenceMatcher
from typing import Dict,List,Tuple
from v5_tab_filters import field,content_tokens,RULES,best_tab,RANKING_SURFACES,legislation_id

def norm_title(item:ET.Element)->str:
    t=field(item,"title").lower();t=re.sub(r"\s+-\s+[^-]{2,45}$","",t);return re.sub(r"[^a-z0-9]+"," ",t).strip()
def article_url(item:ET.Element)->str:
    u=(field(item,"link") or field(item,"resolvedPublisherUrl")).strip().lower()
    if not u:return ""
    u=re.sub(r"[?#].*$","",u).rstrip("/")
    try:
        p=urllib.parse.urlparse(u)
        if p.path in {"","/"}:return ""
    except Exception:return ""
    return u
def template_family(item:ET.Element)->str:
    t=norm_title(item)
    for k in ("obituary","lottery","winning numbers","prediction","picks odds","things to do","job postings"):
        if k in t:return k
    return ""
def _features(item:ET.Element)->dict:
    toks=content_tokens(item);title=norm_title(item)
    return {"title":title,"url":article_url(item),"tokens":toks,"title_tokens":{t for t in title.split() if len(t)>=4},"anchors":{x for x in toks if any(c.isdigit() for c in x) or len(x)>=9},"tab":field(item,"category").lower(),"bill":legislation_id(item),"template":template_family(item)}
def event_similarity(a:ET.Element,b:ET.Element,fa:dict|None=None,fb:dict|None=None)->float:
    fa=fa or _features(a);fb=fb or _features(b)
    if fa["url"] and fa["url"]==fb["url"]:return 1.0
    if fa["title"] and fa["title"]==fb["title"]:return 1.0
    A,B=fa["tokens"],fb["tokens"];tr=SequenceMatcher(None,fa["title"],fb["title"]).ratio();jac=len(A&B)/max(1,len(A|B));score=.62*tr+.38*jac
    if len(fa["anchors"]&fb["anchors"])>=2:score+=.06
    return min(1.,round(score,4))
def same_event(a:ET.Element,b:ET.Element,fa:dict|None=None,fb:dict|None=None)->bool:
    fa=fa or _features(a);fb=fb or _features(b)
    if fa["bill"] and fb["bill"] and fa["bill"]!=fb["bill"]:return False
    if fa["template"] and fb["template"] and fa["template"]==fb["template"] and fa["title"]!=fb["title"]:return False
    if fa["url"] and fa["url"]==fb["url"]:return True
    if fa["title"] and fa["title"]==fb["title"]:return True
    shared_title=fa["title_tokens"]&fb["title_tokens"];shared_all=fa["tokens"]&fb["tokens"]
    if len(shared_title)<3 or len(shared_all)<4:return False
    s=event_similarity(a,b,fa,fb)
    if s>=.82:return True
    if s<.76:return False
    wa,_,_=best_tab(a);wb,_,_=best_tab(b)
    return wa is not None and wa==wb and RULES[wa].specificity>=8 and len(fa["anchors"]&fb["anchors"])>=1
def _candidate_pairs(group:List[ET.Element],cross_tab_only:bool=False):
    feats=[_features(x) for x in group];inv=defaultdict(list);hits=Counter();urlpairs=set()
    for idx,f in enumerate(feats):
        for tok in f["title_tokens"]|f["anchors"]:
            for prior in inv[tok]:
                if not cross_tab_only or feats[prior]["tab"]!=f["tab"]:hits[(prior,idx)]+=1
            inv[tok].append(idx)
    urls=defaultdict(list)
    for idx,f in enumerate(feats):
        if not f["url"]:continue
        for prior in urls[f["url"]]:
            if not cross_tab_only or feats[prior]["tab"]!=f["tab"]:urlpairs.add((prior,idx))
        urls[f["url"]].append(idx)
    pairs=set(urlpairs);pairs.update(p for p,n in hits.items() if n>=3);return feats,sorted(pairs)
def dedupe_within_tabs(items:List[ET.Element])->Tuple[List[ET.Element],List[dict]]:
    kept=[];removed=[];by=defaultdict(list)
    for x in items:by[field(x,"category").lower()].append(x)
    for tab,group in by.items():
        feats,pairs=_candidate_pairs(group);dup={}
        for i,j in pairs:
            if j in dup:continue
            root=i
            while root in dup:root=dup[root]
            if same_event(group[root],group[j],feats[root],feats[j]):dup[j]=root
        for i,x in enumerate(group):
            if i not in dup:kept.append(x)
            else:
                r=dup[i];removed.append({"scope":"within-tab","tab":tab,"removed":field(x,"title"),"kept":field(group[r],"title"),"similarity":event_similarity(x,group[r],feats[i],feats[r])})
    return kept,removed
def cross_tab_clusters(items:List[ET.Element])->List[List[ET.Element]]:
    normal=[x for x in items if field(x,"category").lower() not in RANKING_SURFACES];feats,pairs=_candidate_pairs(normal,True);parent=list(range(len(normal)))
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for i,j in pairs:
        if same_event(normal[i],normal[j],feats[i],feats[j]):
            a,b=find(i),find(j)
            if a!=b:parent[b]=a
    groups=defaultdict(list)
    for i,x in enumerate(normal):groups[find(i)].append(x)
    return [g for g in groups.values() if len(g)>1 and len({field(x,'category').lower() for x in g})>1]
