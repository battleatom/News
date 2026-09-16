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


def technology_has_enough_information(story: Story) -> bool:
    """Reject only Technology cards where both headline and feed summary are effectively empty of context."""
    title=normalize_title(story.title);summary=normalize_title(story.summary);source=normalize_title(story.source)
    if not title:return False
    residual=summary
    for token in sorted((title,source),key=len,reverse=True):
        if token:residual=residual.replace(token," ")
    residual=re.sub(r"\s+"," ",residual).strip()
    title_words=[w for w in title.split() if len(w)>=3]
    residual_words=[w for w in residual.split() if len(w)>=3]
    if len(title_words)>=5 or len(title)>=42:return True
    return len(residual_words)>=8 and len(residual)>=55


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


def _source_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+","",(value or "").lower())


def _coverage_gap_score(source_count: int) -> int:
    if source_count <= 0:return 96
    if source_count == 1:return 92
    if source_count == 2:return 86
    if source_count == 3:return 80
    if source_count == 4:return 74
    if source_count == 5:return 68
    if source_count == 6:return 60
    if source_count == 7:return 52
    if source_count == 8:return 44
    if source_count <= 10:return 34
    if source_count <= 14:return 22
    return 12


def _coverage_label(source_count: int) -> str:
    if source_count == 0:return "High underreporting signal"
    if source_count <= 2:return "Possible underreported — limited corroboration"
    if source_count <= 6:return "Growing supporting coverage"
    if source_count <= 9:return "Broadening coverage"
    return "Broad coverage — underreported signal weakening"


def _related_score(primary: Story, other: Story) -> float:
    a,b=title_terms(primary.title),title_terms(other.title)
    if not a or not b:return 0.0
    overlap=len(a&b)
    if overlap<2:return 0.0
    return overlap/max(1,min(len(a),len(b)))


def _what_next(summary: str) -> str:
    cues=("will ","plans to","expected","scheduled","deadline","next ","later ","tomorrow","vote","hearing","trial","meeting","announce","decision")
    for sentence in re.split(r"(?<=[.!?])\s+",summary or ""):
        if len(sentence.strip())>=45 and any(cue in sentence.lower() for cue in cues):
            return sentence.strip()
    return ""


def enrich_underreported(stories: list[Story], now: datetime) -> None:
    """Build V6 Underreported evidence packages from the already-collected normalized story pool."""
    for story in stories:
        if story.category!="underreported":continue
        candidates=[]
        primary_source=_source_key(story.source)
        for other in stories:
            if other.id==story.id or normalize_url(other.url)==normalize_url(story.url):continue
            score=_related_score(story,other)
            if score<0.40:continue
            skey=_source_key(other.source)
            if not skey or skey==primary_source:continue
            candidates.append((score,other.published_dt,other))
        candidates.sort(key=lambda row:(row[0],row[1]),reverse=True)
        distinct=[];seen_sources=set();seen_urls=set()
        for score,_,other in candidates:
            skey=_source_key(other.source);url=normalize_url(other.url)
            if skey in seen_sources or url in seen_urls:continue
            seen_sources.add(skey);seen_urls.add(url);distinct.append(other)
            if len(distinct)>=24:break
        support_count=len(distinct)
        display=distinct[:4]
        story.coverage_score=_coverage_gap_score(support_count)
        story.coverage_label=_coverage_label(support_count)
        story.supporting_source_count=support_count
        story.what_happened=story.summary if len(story.summary.strip())>=40 else f"The available report identifies this development: {story.title}."
        if support_count<=2:
            story.what_is_missing=(f"Only {support_count} independent supporting publisher{'s were' if support_count!=1 else ' was'} found in the collected V6 source pool. "
                                   "That is enough to flag a possible coverage gap, but not enough to make a high-confidence underreporting claim.")
        else:
            story.what_is_missing=(f"The story has {support_count} independent supporting publishers in the collected V6 source pool. "
                                   "That corroboration helps verify the event while showing how widely the issue has spread beyond the primary report.")
        older=[r for r in distinct if r.published_dt<story.published_dt]
        if older:
            oldest=min(older,key=lambda r:r.published_dt)
            age_days=max(1,(story.published_dt-oldest.published_dt).days)
            story.background=f"Related approved-source reporting reaches back about {age_days} day{'s' if age_days!=1 else ''}. The oldest matched report was from {oldest.source}: {oldest.title}."
        else:
            story.background="No older matched report was identified in the current V6 source pool. This appears to be a newer development and the background section will deepen as related reporting is collected."
        story.what_next=_what_next(story.summary)
        story.related=[{"title":r.title,"url":r.url,"source":r.source,"published_at":r.published_at} for r in display]


def process(stories: list[Story], registry: dict, *, now: datetime | None=None) -> list[Story]:
    now=now or datetime.now(timezone.utc);valid_categories=set(registry["categories"]);cleaned=[]
    for story in stories:
        if story.category not in valid_categories: continue
        story.title=re.sub(r"\s+"," ",story.title).strip();story.summary=re.sub(r"\s+"," ",story.summary).strip();story.url=normalize_url(story.url)
        if not story.title or not story.url or not relevant_to_category(story): continue
        if story.category=="technology" and not technology_has_enough_information(story): continue
        story.importance=importance_score(story,now);story.why_matters=why_matters(story);cleaned.append(story)
    enrich_underreported(cleaned,now)
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
