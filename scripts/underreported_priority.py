#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from update_news import UNDERREPORTED_DISCOVERY_QUERIES, source_is_trusted, underreported_source_allowed

NEWS = Path("News")
MAX_DAYS = 14
MAX_ITEMS = 30


def clean(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str | None):
    try:
        dt = parsedate_to_datetime(clean(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def norm_title(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def feed_url(query: str) -> str:
    q = urllib.parse.quote(f"{query} when:{MAX_DAYS}d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def discover() -> None:
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")

    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - MAX_DAYS * 86400
    seen_titles = {norm_title(clean(i.findtext("title"))) for i in channel.findall("item")}
    seen_links = {clean(i.findtext("link")) for i in channel.findall("item")}
    added = 0

    for source_name, query in UNDERREPORTED_DISCOVERY_QUERIES:
        try:
            req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 UnderreportedPriority/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                feed = ET.fromstring(response.read())
        except Exception as exc:
            print(f"Underreported 14-day discovery failed for {source_name}: {exc}")
            continue

        for src in feed.findall(".//item"):
            title = clean(src.findtext("title"))
            link = clean(src.findtext("link"))
            desc = clean(src.findtext("description"))
            pub = clean(src.findtext("pubDate"))
            dt = parse_date(pub)
            source_el = src.find("source")
            source = source_name or clean(source_el.text if source_el is not None else "")
            if not title or not link or not dt or dt.timestamp() < cutoff or dt > now:
                continue
            if not source_is_trusted(source):
                continue
            candidate = {"title": title, "description": desc, "source": source}
            if not underreported_source_allowed(candidate):
                continue
            nt = norm_title(title)
            if nt in seen_titles or link in seen_links:
                continue
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = link
            ET.SubElement(item, "description").text = desc
            ET.SubElement(item, "pubDate").text = pub
            ET.SubElement(item, "source").text = source
            ET.SubElement(item, "category").text = "underreported"
            seen_titles.add(nt)
            seen_links.add(link)
            added += 1

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Underreported 14-day discovery added {added} candidate story/stories.")


def importance_score(item: ET.Element) -> int:
    text = f"{clean(item.findtext('title'))} {clean(item.findtext('description'))}".lower()
    score = 20
    weighted = {
        "war": 16, "attack": 14, "airstrike": 14, "missile": 14, "ceasefire": 12,
        "mass shooting": 18, "shooting": 12, "killed": 10, "deaths": 10,
        "earthquake": 15, "hurricane": 15, "tornado": 14, "wildfire": 14, "flood": 10,
        "outbreak": 12, "recall": 10, "contamination": 13, "public health": 12,
        "supreme court": 14, "ruling": 11, "executive order": 12, "legislation": 10,
        "bill": 8, "audit": 12, "investigation": 13, "inspector general": 14,
        "whistleblower": 13, "civil rights": 12, "privacy": 10, "surveillance": 11,
        "medicaid": 11, "medicare": 11, "hospital": 9, "housing": 9,
        "workers": 8, "labor": 8, "layoffs": 8, "bankruptcy": 10,
        "pollution": 11, "water": 8, "drought": 9, "tribal": 10, "indigenous": 10,
        "fraud": 10, "settlement": 8, "lawsuit": 8, "election": 10, "voting": 9,
        "humanitarian": 12, "famine": 15, "refugee": 10,
    }
    for term, weight in weighted.items():
        if term in text:
            score += weight
    if any(x in text for x in ("opinion", "review", "podcast", "how to", "guide", "sale", "deal")):
        score -= 18
    return max(0, min(100, score))


def freshness_score(dt, now) -> int:
    if not dt:
        return 0
    age_days = max(0.0, (now - dt).total_seconds() / 86400)
    return max(0, min(100, round(100 * (1 - age_days / MAX_DAYS))))


def age_band(dt, now) -> str:
    if not dt:
        return "unknown"
    d = max(0.0, (now - dt).total_seconds() / 86400)
    if d <= 2: return "blue"
    if d <= 4: return "green"
    if d <= 7: return "orange"
    if d <= 10: return "purple"
    return "red"


def set_text(item: ET.Element, tag: str, value) -> None:
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = str(value)


def rank() -> None:
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")
    now = datetime.now(timezone.utc)
    all_items = list(channel.findall("item"))
    top = [x for x in all_items if clean(x.findtext("category")).lower() == "top"]
    under = [x for x in all_items if clean(x.findtext("category")).lower() == "underreported"]
    rest = [x for x in all_items if clean(x.findtext("category")).lower() not in {"top", "underreported"}]

    ranked = []
    for item in under:
        dt = parse_date(item.findtext("pubDate"))
        age_days = (now - dt).total_seconds() / 86400 if dt else 999
        if age_days > MAX_DAYS:
            continue
        importance = importance_score(item)
        freshness = freshness_score(dt, now)
        try:
            under_score = int(float(clean(item.findtext("underreportedScore")) or 70))
        except Exception:
            under_score = 70
        priority = round(importance * 0.45 + freshness * 0.30 + under_score * 0.25)
        band = age_band(dt, now)
        set_text(item, "importanceScore", importance)
        set_text(item, "freshnessScore", freshness)
        set_text(item, "underreportedPriority", priority)
        set_text(item, "ageBand", band)
        ranked.append((priority, freshness, under_score, dt.timestamp() if dt else 0, item))

    ranked.sort(key=lambda row: (row[0], row[1], row[2], row[3]), reverse=True)
    selected = [row[-1] for row in ranked[:MAX_ITEMS]]

    for item in all_items:
        channel.remove(item)
    for item in top + selected + rest:
        channel.append(item)
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Underreported priority ranking retained {len(selected)} stories from the last {MAX_DAYS} days.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--rank", action="store_true")
    args = parser.parse_args()
    if args.discover:
        discover()
    elif args.rank:
        rank()
    else:
        raise SystemExit("Use --discover or --rank")


if __name__ == "__main__":
    main()
