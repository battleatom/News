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

def google_news_url(query: str) -> str:
    q = urllib.parse.quote(f"{query} when:7d")
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
    return stories, errors
