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


def _hard_dedupe(rows:list[Story],near_duplicate)->list[Story]:
    """Hard-remove only duplicate/near-identical event coverage."""
    canonical=[]
    for story in rows:
        if any(near_duplicate(story,prior) or same_event(story,prior) for prior in canonical):
            continue
        canonical.append(story)
    return canonical


def select_diverse(rows:list[Story],target:int,source_cap:int,near_duplicate)->list[Story]:
    """Keep real inventory while reordering repeated publishers/topics behind variety.

    True same-event duplicates are removed. Publisher/topic repetition is soft: stories are
    deferred and can return later in the tab so diversity never destroys valid inventory.
    """
    candidates=_hard_dedupe(rows,near_duplicate)
    if not candidates or target<=0:return []
    tracked=_tracked_topics(candidates)
    chosen=[];chosen_ids=set();source_counts=defaultdict(int);topic_counts=defaultdict(int)

    def add(story:Story)->None:
        chosen.append(story);chosen_ids.add(id(story))
        source_counts[_norm(story.source) or "unknown"]+=1
        for term in (_title_terms(story)&tracked):topic_counts[term]+=1

    # Pass 1: build a varied lead section. Conflicts are deferred, never discarded.
    lead_target=min(20,target)
    for story in candidates:
        if len(chosen)>=lead_target:break
        source_key=_norm(story.source) or "unknown"
        topics=_title_terms(story)&tracked
        if source_counts[source_key]>=min(source_cap,2):continue
        if topics and any(topic_counts[term]>=2 for term in topics):continue
        add(story)

    # Pass 2: continue with moderate topic spacing and the normal publisher cap.
    for story in candidates:
        if len(chosen)>=target:break
        if id(story) in chosen_ids:continue
        source_key=_norm(story.source) or "unknown"
        topics=_title_terms(story)&tracked
        if source_counts[source_key]>=source_cap:continue
        if topics and any(topic_counts[term]>=4 for term in topics):continue
        add(story)

    # Pass 3: fill remaining slots from deferred valid stories. Topic limits are now
    # intentionally relaxed; source caps and hard event dedupe still remain enforced.
    for story in candidates:
        if len(chosen)>=target:break
        if id(story) in chosen_ids:continue
        source_key=_norm(story.source) or "unknown"
        if source_counts[source_key]>=source_cap:continue
        add(story)

    return chosen
