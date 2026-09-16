from __future__ import annotations
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from model import Story

TOPIC_STOP={
    "about","after","against","amid","among","before","could","first","latest","major","more","new","news","report","reports","says","said","story","today","update","updates","with","without",
    "world","united","states","federal","government","president","presidential","white","house","official","officials","court","supreme","state","local","regional","region",
    "technology","tech","gaming","game","games","entertainment","military","defense","movie","movies","season","week","year","years","people","company","companies"
}


def _norm(value:str)->str:
    return re.sub(r"[^a-z0-9]+"," ",(value or "").lower()).strip()


def _title_terms(story:Story)->set[str]:
    return {w for w in _norm(story.title).split() if len(w)>=4 and w not in TOPIC_STOP}


def same_event(a:Story,b:Story)->bool:
    """Catch materially identical coverage even when headlines are not near-identical."""
    ta,tb=_title_terms(a),_title_terms(b)
    if not ta or not tb:return False
    shared=ta&tb
    smaller=max(1,min(len(ta),len(tb)))
    overlap=len(shared)/smaller
    ratio=SequenceMatcher(None,_norm(a.title),_norm(b.title)).ratio()
    if len(shared)>=5 and overlap>=.62:return True
    if len(shared)>=4 and overlap>=.72 and ratio>=.66:return True
    if len(shared)>=3 and overlap>=.75 and ratio>=.80:return True
    return False


def _tracked_topics(rows:list[Story])->set[str]:
    counts=Counter(term for story in rows for term in _title_terms(story))
    upper=max(4,int(len(rows)*.45))
    return {term for term,count in counts.items() if 3<=count<=upper}


def select_diverse(rows:list[Story],target:int,source_cap:int,near_duplicate)->list[Story]:
    """Select a varied tab: canonical event coverage, publisher spread and topic spread."""
    tracked=_tracked_topics(rows)
    chosen=[];source_counts=defaultdict(int);topic_counts=defaultdict(int)
    for story in rows:
        source_key=_norm(story.source) or "unknown"
        top_window=len(chosen)<20
        publisher_limit=min(source_cap,2) if top_window else source_cap
        if source_counts[source_key]>=publisher_limit:continue
        if any(near_duplicate(story,prior) or same_event(story,prior) for prior in chosen):continue
        topics=_title_terms(story)&tracked
        topic_limit=2 if top_window else 4
        if topics and any(topic_counts[term]>=topic_limit for term in topics):continue
        chosen.append(story);source_counts[source_key]+=1
        for term in topics:topic_counts[term]+=1
        if len(chosen)>=target:break
    return chosen
