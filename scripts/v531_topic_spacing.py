#!/usr/bin/env python3
"""Topic-spacing pass for Technology and Gaming.

Every story is retained. Existing editorial order remains the baseline. A story
is deferred when it repeats the same event/product topic seen recently, or when
it would create an immediate run of the same broad brand/platform.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

NEWS = Path("News")
REPORT = Path("/tmp/v531-topic-spacing-report.json")
TARGETS = {"technology", "gaming"}
EVENT_WINDOW = 4
BRAND_WINDOW = 1
LOOKAHEAD = 18
MAX_QUALITY_DROP = 10.0

TECH_BRANDS = ("openai","chatgpt","anthropic","claude","nvidia","microsoft","apple","iphone","google","pixel","android","samsung","galaxy","meta","tiktok","tesla","spacex")
GAMING_BRANDS = ("nintendo","switch","playstation","ps5","xbox","steam","valve","epic games","battle.net")
EVENT_PHRASES = (
    "007 first light","james bond","steam frame","steam deck","game pass","ps plus","subscription cancellations",
    "persona 4","persona 5","persona 6","zelda","ocarina of time","metroid dread","diablo iv","runescape dragonwilds",
    "windows 11","ios 27","iphone 18","pixel 11","data breach","ai slowdown","kill switch","glass imaging",
)

STOP = {
    "the","and","for","with","from","into","about","after","before","this","that","these","those",
    "new","news","latest","update","updates","report","reports","says","said","will","could","would","should",
    "how","why","what","when","where","who","your","our","their","its","has","have","had","was","were",
    "are","is","to","of","in","on","at","by","as","a","an","or","but","not","more","most","best",
    "technology","tech","gaming","game","games","review","reviews","first","look","watch","video",
    "release","releases","released","coming","available","edition","year","years","2026","2027",
}
LOW_VALUE_TITLE = re.compile(r"\b(best|top[- ]rated|all the|everything we know|guide|deals?|sale|discount|coupon)\b", re.I)


def text(item, tag): return (item.findtext(tag) or "").strip()
def title(item): return text(item,"title")
def category(item): return text(item,"category").lower()

def quality(item):
    try: return float(text(item,"v53QualityScore"))
    except Exception:
        try: return float(text(item,"sourceQualityScore"))*0.75
        except Exception: return 50.0

def candidate_quality(item):
    return quality(item) - (10 if LOW_VALUE_TITLE.search(title(item)) else 0)

def brand_set(item):
    raw=title(item).lower(); cat=category(item)
    brands=TECH_BRANDS if cat=="technology" else GAMING_BRANDS
    return {b for b in brands if b in raw}

def event_fingerprint(item):
    raw=title(item).lower()
    phrases={p for p in EVENT_PHRASES if p in raw}
    words={w for w in re.findall(r"[a-z0-9]+",raw) if len(w)>=4 and w not in STOP and w not in {"nintendo","switch","playstation","xbox","steam","openai","anthropic","microsoft","apple","google"}}
    return phrases,words

def event_similarity(a,b):
    pa,wa=event_fingerprint(a); pb,wb=event_fingerprint(b)
    if pa & pb: return 1.0
    if not wa or not wb: return 0.0
    shared=wa & wb
    if len(shared)<2: return 0.0
    return len(shared)/max(1,min(len(wa),len(wb)))

def hard_conflict(candidate,recent):
    return any(event_similarity(candidate,p)>=0.50 for p in recent[-EVENT_WINDOW:])

def soft_brand_conflict(candidate,recent):
    cb=brand_set(candidate)
    if not cb: return False
    return any(cb & brand_set(p) for p in recent[-BRAND_WINDOW:])

def conflicts(candidate,recent):
    return hard_conflict(candidate,recent) or soft_brand_conflict(candidate,recent)

def spaced(items):
    remaining=list(items); out=[]
    while remaining:
        recent=out[-EVENT_WINDOW:]; current=remaining[0]
        if not conflicts(current,recent):
            out.append(remaining.pop(0)); continue
        floor=candidate_quality(current)-MAX_QUALITY_DROP
        pick=None
        for idx,candidate in enumerate(remaining[1:LOOKAHEAD],start=1):
            if not conflicts(candidate,recent) and candidate_quality(candidate)>=floor:
                pick=idx; break
        out.append(remaining.pop(pick if pick is not None else 0))
    return out

def metrics(items,limit=25):
    arr=items[:limit]; event=0; adjacent_brand=0; examples=[]
    for i,item in enumerate(arr):
        recent=arr[max(0,i-EVENT_WINDOW):i]
        ev=[(p,event_similarity(item,p)) for p in recent if event_similarity(item,p)>=0.50]
        if ev:
            event+=1
            if len(examples)<10:
                p,s=max(ev,key=lambda x:x[1]); examples.append({"type":"event","story":title(item),"near":title(p),"similarity":round(s,2)})
        if i and brand_set(item)&brand_set(arr[i-1]):
            adjacent_brand+=1
            if len(examples)<10: examples.append({"type":"adjacent-brand","story":title(item),"near":title(arr[i-1])})
    return event,adjacent_brand,examples

def displacement(before,after,limit=25):
    old={id(item):i for i,item in enumerate(before)}
    vals=[abs(i-old[id(item)]) for i,item in enumerate(after[:limit])]
    return round(sum(vals)/len(vals),2) if vals else 0

def main():
    tree=ET.parse(NEWS); channel=tree.getroot().find("channel")
    if channel is None: raise SystemExit("RSS channel not found")
    items=list(channel.findall("item")); by_cat=defaultdict(list)
    for item in items: by_cat[category(item)].append(item)
    replacements={}; report={"policy":{"targets":sorted(TARGETS),"eventWindow":EVENT_WINDOW,"brandWindow":BRAND_WINDOW,"lookahead":LOOKAHEAD,"maxQualityDrop":MAX_QUALITY_DROP,"deletes":0,"ranking":"baseline order with event spacing and adjacent-brand spacing"},"tabs":{}}
    for cat in TARGETS:
        before=by_cat.get(cat,[]); after=spaced(before); replacements[cat]=iter(after)
        be,bb,bx=metrics(before); ae,ab,ax=metrics(after)
        report["tabs"][cat]={"count":len(before),"beforeEventConflictsTop25":be,"afterEventConflictsTop25":ae,"beforeAdjacentBrandConflictsTop25":bb,"afterAdjacentBrandConflictsTop25":ab,"combinedBefore":be+bb,"combinedAfter":ae+ab,"averageTop25Displacement":displacement(before,after),"beforeTop25":[title(x) for x in before[:25]],"afterTop25":[title(x) for x in after[:25]],"beforeExamples":bx,"afterExamples":ax}
    for item in items: channel.remove(item)
    for item in items:
        cat=category(item); channel.append(next(replacements[cat]) if cat in TARGETS else item)
    tree.write(NEWS,encoding="utf-8",xml_declaration=True)
    REPORT.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
