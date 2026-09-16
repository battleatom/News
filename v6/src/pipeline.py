from __future__ import annotations
import re
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher

from model import Story
from relevance import relevant_to_category

TRACKING = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid"}
IMPACT_TERMS = {
    "war":18,"invasion":18,"attack":16,"airstrike":16,"missile":16,"ceasefire":15,
    "crisis":12,"emergency":12,"sanctions":10,"tariff":10,"shutdown":12,"supreme court":14,
    "executive order":12,"election":12,"earthquake":15,"hurricane":15,"tornado":14,"wildfire":14,
    "shooting":12,"killed":10,"outage":10,"breach":12,"hack":12,"cyberattack":15,
    "lawsuit":8,"ruling":10,"ban":9,"recall":10,"layoffs":8,"bankruptcy":12,
    "inflation":8,"recession":12,"contamination":12,"acquisition":12,"closure":14,
    "canceled":10,"cancelled":10,"delay":8,"delayed":8,
}
ROUTINE_TERMS = {"opinion":-10,"review":-8,"podcast":-8,"how to":-8,"photos":-5,"best":-5,"guide":-5,"sale":-8,"deal":-8}

def normalize_url(value: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(value.strip())
        query = [(k,v) for k,v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in TRACKING]
        return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), urllib.parse.urlencode(query), ""))
    except Exception:
        return value.strip()

def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

def title_terms(value: str) -> set[str]:
    stop={"the","and","for","with","from","into","after","before","about","this","that","says","said","new","news","latest","update","report","reports","world","fixture","event","technology","local","story"}
    return {w for w in normalize_title(value).split() if len(w)>=3 and w not in stop}

def near_duplicate(a: Story, b: Story) -> bool:
    if normalize_url(a.url) and normalize_url(a.url) == normalize_url(b.url):
        return True
    ta,tb=title_terms(a.title),title_terms(b.title)
    if not ta or not tb:
        return False
    smaller=min(len(ta),len(tb))
    if smaller>=5 and len(ta&tb)/smaller>=0.86:
        return True
    aa,bb=normalize_title(a.title),normalize_title(b.title)
    return len(ta & tb)>=4 and min(len(aa),len(bb))>=35 and SequenceMatcher(None,aa,bb).ratio()>=0.92

def age_hours(story: Story, now: datetime) -> float:
    return max(0.0, (now - story.published_dt).total_seconds()/3600)

def importance_score(story: Story, now: datetime) -> float:
    text=f"{story.title} {story.summary}".lower();score=0.0
    for term,weight in IMPACT_TERMS.items():
        if term in text: score += weight
    for term,weight in ROUTINE_TERMS.items():
        if term in text: score += weight
    score += max(0.0, 18.0 - age_hours(story,now)/8.0)
    if story.category=="underreported": score += 5
    if story.category=="legislation" and any(x in story.source.lower() for x in ("congress","federal register","white house","govinfo")): score += 10
    return round(score,2)

def why_matters(story: Story) -> str:
    text=f"{story.title} {story.summary}".lower();hits=[term for term in IMPACT_TERMS if term in text][:2]
    if hits: return f"This report involves {' and '.join(hits)}; the linked source has the underlying details and latest updates."
    if story.category=="legislation": return "This is an official-policy or legislation item that may change rules, government action, or legal requirements."
    if story.category in {"local","region","nm"}: return "This story is included because it has direct state or regional relevance and may affect nearby communities."
    if story.category=="technology": return "This could affect technology products, services, security, or the companies behind them."
    if story.category=="gaming": return "This could affect games, hardware, studios, releases, pricing, or platform users."
    if story.category=="military": return "This concerns defense, armed forces, security, or an active conflict and may have broader policy or safety implications."
    if story.category=="entertainment": return "This is a current entertainment-industry development involving a release, creator, company, event, or public figure."
    return "This is a current development selected for recency, source quality, and potential public impact."

def process(stories: list[Story], registry: dict, *, now: datetime | None=None) -> list[Story]:
    now=now or datetime.now(timezone.utc);valid_categories=set(registry["categories"]);cleaned=[]
    for story in stories:
        if story.category not in valid_categories: continue
        story.title=re.sub(r"\s+"," ",story.title).strip();story.summary=re.sub(r"\s+"," ",story.summary).strip();story.url=normalize_url(story.url)
        if not story.title or not story.url or not relevant_to_category(story): continue
        story.importance=importance_score(story,now);story.why_matters=why_matters(story);cleaned.append(story)
    by_cat=defaultdict(list)
    for story in cleaned: by_cat[story.category].append(story)
    output=[]
    for category, rows in by_cat.items():
        cfg=registry["categories"][category];target=int(cfg.get("target",50));source_cap=int(cfg.get("source_cap",8))
        rows.sort(key=lambda s:(s.importance,s.published_dt), reverse=True);chosen=[];source_counts=defaultdict(int)
        for story in rows:
            source_key=re.sub(r"[^a-z0-9]+"," ",story.source.lower()).strip() or "unknown"
            if source_counts[source_key]>=source_cap or any(near_duplicate(story,prior) for prior in chosen): continue
            chosen.append(story);source_counts[source_key]+=1
            if len(chosen)>=target: break
        output.extend(chosen)
    category_order={name:i for i,name in enumerate(registry["categories"])}
    output.sort(key=lambda s:(category_order[s.category], -s.importance, -s.published_dt.timestamp()))
    return output
