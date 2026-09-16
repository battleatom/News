from __future__ import annotations
import re
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher

from model import Story
from relevance import relevant_to_category
from diversity import select_diverse

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
UNDERREPORTED_WEIGHTED = {
    "war":16,"attack":14,"airstrike":14,"missile":14,"ceasefire":12,"mass shooting":18,"shooting":12,
    "killed":10,"deaths":10,"earthquake":15,"hurricane":15,"tornado":14,"wildfire":14,"flood":10,
    "outbreak":12,"recall":10,"contamination":13,"public health":12,"supreme court":14,"ruling":11,
    "executive order":12,"legislation":10,"bill":8,"audit":12,"investigation":13,"inspector general":14,
    "whistleblower":13,"civil rights":12,"privacy":10,"surveillance":11,"medicaid":11,"medicare":11,
    "hospital":9,"housing":9,"workers":8,"labor":8,"layoffs":8,"bankruptcy":10,"pollution":11,"water":8,
    "drought":9,"tribal":10,"indigenous":10,"fraud":10,"settlement":8,"lawsuit":8,"election":10,"voting":9,
    "humanitarian":12,"famine":15,"refugee":10,
}
CONTINUING_TERMS = {
    "investigation","investigating","lawsuit","court","ruling","appeal","trial","hearing","audit","whistleblower",
    "recall","outbreak","wildfire","drought","flood","war","ceasefire","humanitarian","pollution","cleanup",
    "surveillance","medicaid","medicare","housing","election","voting","legislation","bill","regulation","regulator",
    "bankruptcy","layoffs","strike","workers","civil rights","indigenous",
}


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


def _summary_residual(story: Story) -> str:
    summary=normalize_title(story.summary);title=normalize_title(story.title);source=normalize_title(story.source)
    residual=summary
    for token in sorted((title,source),key=len,reverse=True):
        if token:residual=residual.replace(token," ")
    return re.sub(r"\s+"," ",residual).strip()


def technology_has_enough_information(story: Story) -> bool:
    title=normalize_title(story.title);residual=_summary_residual(story)
    if not title:return False
    title_words=[w for w in title.split() if len(w)>=3]
    residual_words=[w for w in residual.split() if len(w)>=3]
    if len(title_words)>=5 or len(title)>=42:return True
    return len(residual_words)>=8 and len(residual)>=55


def age_hours(story: Story, now: datetime) -> float:
    return max(0.0, (now - story.published_dt).total_seconds()/3600)


def presidential_has_enough_information(story: Story, now: datetime) -> bool:
    if age_hours(story,now)<=14*24:return True
    residual=_summary_residual(story)
    return len(residual)>=45 and len([w for w in residual.split() if len(w)>=3])>=7


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


def _parse_dt(value: str) -> datetime:
    try:
        dt=datetime.fromisoformat((value or "").replace("Z","+00:00"))
    except Exception:
        return datetime.fromtimestamp(0,tz=timezone.utc)
    if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
    if source_count == 0:return "High coverage-gap signal · uncorroborated"
    if source_count <= 2:return "Possible underreported · limited corroboration"
    if source_count <= 6:return "Growing supporting coverage"
    if source_count <= 9:return "Broadening coverage"
    return "Broad coverage · underreported signal weakening"


def _corroboration_score(count: int) -> int:
    if count<=0:return 15
    if count==1:return 40
    if count==2:return 65
    if count==3:return 80
    if count==4:return 90
    return 100


def _freshness_score(dt: datetime, now: datetime) -> int:
    age=max(0.0,(now-dt).total_seconds()/3600)
    if age<=6:return 100
    if age<=24:return 95
    if age<=48:return 88
    if age<=72:return 78
    if age<=120:return 62
    if age<=168:return 48
    if age<=240:return 32
    if age<=14*24:return 15
    return 0


def _saturation_penalty(count: int) -> int:
    if count<=6:return 0
    if count<=9:return 4
    if count<=14:return 10
    return 18


def _underreported_importance(story: Story) -> int:
    text=f"{story.title} {story.summary}".lower();score=20
    for term,weight in UNDERREPORTED_WEIGHTED.items():
        if term in text:score+=weight
    if any(term in text for term in ("opinion","review","podcast","how to","guide","sale","deal")):score-=18
    return max(0,min(100,score))


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


def _coverage_windows(related: list[dict], primary_source: str, now: datetime) -> tuple[int,int,int]:
    recent6=set();recent24=set();prior72=set();primary=_source_key(primary_source)
    for row in related:
        skey=_source_key(str(row.get("source","")))
        if not skey or skey==primary:continue
        dt=_parse_dt(str(row.get("published_at","")))
        if dt.timestamp()<=0:continue
        age=max(0.0,(now-dt).total_seconds()/3600)
        if age<=6:recent6.add(skey)
        if age<=24:recent24.add(skey)
        elif age<=72:prior72.add(skey)
    return len(recent6),len(recent24),len(prior72)


def _momentum_score(count: int, recent6: int, recent24: int, prior72: int, related: list[dict]) -> int:
    if recent6>=3:return 100
    if recent6==2:return 92
    if recent24>=5:return 95
    if recent24>=3 and recent24>prior72:return 85
    if recent24>=2 and recent24>=prior72:return 72
    if recent24==1 and prior72<=1:return 55
    if recent24==1:return 40
    if count>0 and not any(_parse_dt(str(r.get("published_at",""))).timestamp()>0 for r in related):return 45
    return 20


def _continuing_score(story: Story, now: datetime) -> int:
    age_days=max(0.0,(now-story.published_dt).total_seconds()/86400)
    score=max(25,70-round(age_days*2.5));text=f"{story.title} {story.summary}".lower()
    if any(term in text for term in CONTINUING_TERMS):score+=18
    if story.what_next:score+=8
    if story.background:score+=5
    return max(0,min(100,score))


def enrich_underreported(visible_stories: list[Story], evidence_pool: list[Story], now: datetime) -> None:
    for story in visible_stories:
        if story.category!="underreported":continue
        evidence=[];primary_source=_source_key(story.source);seen_sources=set();seen_urls=set()
        for row in story.related or []:
            skey=_source_key(str(row.get("source","")));url=normalize_url(str(row.get("url","")))
            if not skey or skey==primary_source or not url or skey in seen_sources or url in seen_urls:continue
            seen_sources.add(skey);seen_urls.add(url);evidence.append(dict(row))
        candidates=[]
        for other in evidence_pool:
            if other.id==story.id or normalize_url(other.url)==normalize_url(story.url):continue
            score=_related_score(story,other)
            if score<0.40:continue
            skey=_source_key(other.source)
            if not skey or skey==primary_source:continue
            candidates.append((score,other.published_dt,other))
        candidates.sort(key=lambda row:(row[0],row[1]),reverse=True)
        for _,_,other in candidates:
            skey=_source_key(other.source);url=normalize_url(other.url)
            if skey in seen_sources or url in seen_urls:continue
            seen_sources.add(skey);seen_urls.add(url)
            evidence.append({"title":other.title,"url":other.url,"source":other.source,"published_at":other.published_at})
            if len(evidence)>=24:break
        support_count=len(evidence);display=evidence[:4]
        story.supporting_source_count=support_count
        story.coverage_gap_score=_coverage_gap_score(support_count)
        story.coverage_label=_coverage_label(support_count)
        story.what_happened=story.summary if len(story.summary.strip())>=40 else f"The available report identifies this development: {story.title}."
        if support_count==0:
            story.what_is_missing="No independent supporting publisher was found in the current approved coverage search. That is a coverage-gap signal, but the story is not treated as strongly corroborated until supporting reporting appears."
        elif support_count<=2:
            story.what_is_missing=f"Only {support_count} independent supporting publisher{'s were' if support_count!=1 else ' was'} found. The story remains lightly covered, but there is at least some independent corroboration."
        else:
            story.what_is_missing=f"The story has {support_count} independent supporting publishers. That corroboration verifies the event while the coverage-gap score measures how broadly it has spread beyond the primary report."
        older=[r for r in evidence if _parse_dt(str(r.get("published_at","")))<story.published_dt and _parse_dt(str(r.get("published_at",""))).timestamp()>0]
        if older:
            oldest=min(older,key=lambda r:_parse_dt(str(r.get("published_at",""))))
            oldest_dt=_parse_dt(str(oldest.get("published_at","")));age_days=max(1,(story.published_dt-oldest_dt).days)
            story.background=f"Related approved-source reporting reaches back about {age_days} day{'s' if age_days!=1 else ''}. The oldest matched report was from {oldest.get('source','another outlet')}: {oldest.get('title','Related reporting')}."
        else:
            story.background="No older matched report was identified in the current evidence pool. This appears to be a newer development and the background section will deepen as related reporting is collected."
        story.what_next=_what_next(story.summary)
        recent6,recent24,prior72=_coverage_windows(evidence,story.source,now)
        story.recent_supporting_sources_6h=recent6;story.recent_supporting_sources_24h=recent24;story.prior_supporting_sources_72h=prior72
        story.corroboration_score=_corroboration_score(support_count)
        story.freshness_score=_freshness_score(story.published_dt,now)
        story.coverage_momentum_score=_momentum_score(support_count,recent6,recent24,prior72,evidence)
        story.continuing_relevance_score=_continuing_score(story,now)
        story.saturation_penalty=_saturation_penalty(support_count)
        importance=_underreported_importance(story)
        priority=round(importance*.25+story.corroboration_score*.20+story.freshness_score*.20+story.coverage_gap_score*.15+story.coverage_momentum_score*.10+story.continuing_relevance_score*.10-story.saturation_penalty)
        story.underreported_priority=max(0,min(100,priority))
        story.coverage_score=story.underreported_priority
        story.related=display


def process(stories: list[Story], registry: dict, *, now: datetime | None=None) -> list[Story]:
    now=now or datetime.now(timezone.utc);valid_categories=set(registry["categories"]);cleaned=[];evidence_pool=[]
    for story in stories:
        if story.category not in valid_categories: continue
        story.title=re.sub(r"\s+"," ",story.title).strip();story.summary=re.sub(r"\s+"," ",story.summary).strip();story.url=normalize_url(story.url)
        if not story.title or not story.url:continue
        evidence_pool.append(story)
        if not relevant_to_category(story): continue
        if story.category=="technology" and not technology_has_enough_information(story): continue
        if story.category=="presidential" and not presidential_has_enough_information(story,now):continue
        story.importance=importance_score(story,now);story.why_matters=why_matters(story);cleaned.append(story)
    enrich_underreported(cleaned,evidence_pool,now)
    by_cat=defaultdict(list)
    for story in cleaned: by_cat[story.category].append(story)
    output=[]
    for category, rows in by_cat.items():
        cfg=registry["categories"][category];target=int(cfg.get("target",50));source_cap=int(cfg.get("source_cap",8))
        if category=="underreported":
            rows.sort(key=lambda s:(s.underreported_priority,s.freshness_score,s.coverage_momentum_score,s.importance,s.corroboration_score,s.published_dt),reverse=True)
        else:
            rows.sort(key=lambda s:(s.importance,s.published_dt), reverse=True)
        if category=="x":
            chosen=[];source_counts=defaultdict(int)
            for story in rows:
                source_key=re.sub(r"[^a-z0-9]+"," ",story.source.lower()).strip() or "unknown"
                if source_counts[source_key]>=source_cap or any(near_duplicate(story,prior) for prior in chosen):continue
                chosen.append(story);source_counts[source_key]+=1
                if len(chosen)>=target:break
        else:
            chosen=select_diverse(rows,target,source_cap,near_duplicate)
        output.extend(chosen)
    category_order={name:i for i,name in enumerate(registry["categories"])}
    output.sort(key=lambda s:(category_order[s.category], -(s.underreported_priority if s.category=="underreported" else s.importance), -s.published_dt.timestamp()))
    return output
