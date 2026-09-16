from __future__ import annotations
import hashlib
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from model import Story

UA = "Underreported-V6/1.0 (+https://battleatom.github.io/)"
TIMEOUT = 15
MAX_WORKERS = 10
EVIDENCE_WORKERS = 6
MAX_UNDERREPORTED_EVIDENCE = 40
MAX_EVIDENCE_POOL = 24

COMMON_TRUSTED = {
    "reuters","associatedpress","apnews","npr","cbsnews","nbcnews","bbc","theguardian","aljazeera",
    "propublica","kffhealthnews","themarshallproject","centerforpublicintegrity","stateline","insideclimatenews",
    "texastribune","newyorktimes","washingtonpost","wallstreetjournal","usatoday","abcnews","cnn","foxnews",
    "politico","axios","bloomberg","forbes","time","newsweek","pbsnewshour","latimes","chicagotribune",
}

def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def parse_date(value: str) -> datetime:
    value = (value or "").strip()
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        dt = parsedate_to_datetime(value)
    except Exception:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.fromtimestamp(0, tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def google_news_url(query: str, days: int = 7) -> str:
    q = urllib.parse.quote(f"{query} when:{days}d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

def request_xml(url: str) -> ET.Element:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return ET.fromstring(response.read())

def source_from_item(item: ET.Element, fallback: str) -> str:
    source = clean_text(item.findtext("source") or "")
    if source:
        return source
    title = clean_text(item.findtext("title") or "")
    if " - " in title:
        maybe = title.rsplit(" - ", 1)[-1].strip()
        if 1 <= len(maybe) <= 80:
            return maybe
    return fallback

def title_from_item(item: ET.Element) -> str:
    title = clean_text(item.findtext("title") or "")
    if " - " in title:
        left, right = title.rsplit(" - ", 1)
        if left.strip() and 1 <= len(right.strip()) <= 80:
            return left.strip()
    return title

def item_link(item: ET.Element) -> str:
    return clean_text(item.findtext("link") or item.findtext("guid") or "")

def story_id(category: str, url: str, title: str) -> str:
    return hashlib.sha1(f"{category}|{url}|{title}".encode("utf-8")).hexdigest()[:20]

def parse_items(root: ET.Element, source_cfg: dict) -> list[Story]:
    rows: list[Story] = []
    for item in root.findall(".//item"):
        title = title_from_item(item)
        url = item_link(item)
        if not title or not url:
            continue
        published = parse_date(item.findtext("pubDate") or item.findtext("published") or "")
        source = source_from_item(item, source_cfg.get("name", "Unknown"))
        summary = clean_text(item.findtext("description") or "")
        category = source_cfg["category"]
        rows.append(Story(
            id=story_id(category, url, title), category=category, title=title, url=url, source=source,
            published_at=published.isoformat().replace("+00:00", "Z"), summary=summary,
            state=str(source_cfg.get("state", "")), region=str(source_cfg.get("region", "")),
            market=str(source_cfg.get("market", "")), source_id=str(source_cfg.get("id", "")),
        ))
    return rows

def collect_one(source_cfg: dict) -> tuple[str, list[Story], str]:
    try:
        url = google_news_url(source_cfg["query"]) if source_cfg["kind"] == "google_news" else source_cfg["url"]
        rows = parse_items(request_xml(url), source_cfg)
        return source_cfg["id"], rows, ""
    except Exception as exc:
        return source_cfg["id"], [], f"{type(exc).__name__}: {exc}"

def _source_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

def _terms(value: str) -> set[str]:
    stop={"the","and","for","with","from","into","after","before","about","this","that","says","said","new","news","latest","update","report","reports","world","united","states","will","are","was","were","has","have","had","not","but","its","their"}
    return {w for w in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(w)>=3 and w not in stop}

def _trusted_keys(registry: dict) -> set[str]:
    keys={_source_key(row.get("name", "")) for row in registry.get("sources", [])}
    return {x for x in keys if x} | COMMON_TRUSTED

def _collect_evidence_for_story(story: Story, trusted: set[str]) -> list[dict]:
    query_words=[w for w in re.findall(r"[A-Za-z0-9]+", story.title) if len(w)>2][:14]
    if len(query_words)<2:
        return []
    target=_terms(story.title)
    primary_source=_source_key(story.source)
    try:
        root=request_xml(google_news_url(" ".join(query_words), 14))
    except Exception:
        return []
    candidates=[]
    now=datetime.now(timezone.utc)
    for item in root.findall(".//item"):
        title=title_from_item(item);url=item_link(item)
        source=source_from_item(item, "")
        if not title or not url or not source:
            continue
        skey=_source_key(source)
        if not skey or skey==primary_source or skey not in trusted:
            continue
        words=_terms(title)
        overlap=len(target & words)
        if overlap<2:
            continue
        published=parse_date(item.findtext("pubDate") or "")
        if published.timestamp()<=0 or published>now:
            continue
        age_hours=max(0.0,(now-published).total_seconds()/3600)
        score=overlap*10+max(0.0,8.0-age_hours/12.0)
        candidates.append((score,published,{"title":title,"url":url,"source":source,"published_at":published.isoformat().replace("+00:00","Z")}))
    candidates.sort(key=lambda row:(row[0],row[1]),reverse=True)
    out=[];seen_sources=set();seen_urls=set()
    for _,_,row in candidates:
        skey=_source_key(row["source"]);url=row["url"]
        if skey in seen_sources or url in seen_urls:
            continue
        seen_sources.add(skey);seen_urls.add(url);out.append(row)
        if len(out)>=MAX_EVIDENCE_POOL:
            break
    return out

def enrich_underreported_evidence(stories: list[Story], registry: dict) -> None:
    candidates=[s for s in stories if s.category=="underreported"][:MAX_UNDERREPORTED_EVIDENCE]
    if not candidates:
        return
    trusted=_trusted_keys(registry)
    with ThreadPoolExecutor(max_workers=min(EVIDENCE_WORKERS,len(candidates))) as executor:
        futures={executor.submit(_collect_evidence_for_story,story,trusted):story for story in candidates}
        for future in as_completed(futures):
            story=futures[future]
            try:
                story.related=future.result()
            except Exception:
                story.related=[]

def collect_all(registry: dict) -> tuple[list[Story], list[dict]]:
    stories: list[Story] = []
    errors: list[dict] = []
    sources = list(registry.get("sources", []))
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(sources)))) as executor:
        futures = {executor.submit(collect_one, source): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            sid, rows, error = future.result()
            stories.extend(rows)
            if error:
                errors.append({"source": sid, "name": source.get("name", sid), "error": error})
    enrich_underreported_evidence(stories, registry)
    return stories, errors
