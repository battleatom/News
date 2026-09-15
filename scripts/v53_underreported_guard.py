#!/usr/bin/env python3
"""V5.3 Underreported evidence guard.

Underreported means a *current* public-interest story with credible but limited
recent independent coverage. Historical reporting is useful background, but it
must not inflate the current supporting-source count.

Policy:
- primary story must already be current (the upstream collector uses 14 days);
- supporting coverage is counted only inside a 90-day evidence window;
- historical (>90 day) matches remain available as background/footnotes only;
- 0 recent independent supporting sources => insufficient evidence, remove from
  Underreported;
- 1 recent source => possible/lower-confidence underreported signal;
- 2-4 recent sources => strongest Underreported zone;
- 5-8 recent sources => diminishing signal as coverage broadens;
- 9+ recent sources => too broadly covered for Underreported, remove.

This script does not mutate D/NR/NW pools and does not touch any other tab.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NEWS = Path("News")
REPORT = Path("/tmp/v53-underreported-guard.json")
RECENT_WINDOW_DAYS = 90
MIN_RECENT_SOURCES = 1
MAX_RECENT_SOURCES = 8


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def parse_date(value: str | None):
    try:
        dt = parsedate_to_datetime(clean(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def source_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def title_key(value: str | None) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", clean(value).lower()))


def canonical_link(value: str | None) -> str:
    value = clean(value)
    value = re.sub(r"([?&])(utm_[^=&]+|fbclid|gclid|mc_[^=&]+)=[^&#]*", "", value, flags=re.I)
    value = re.sub(r"[?&]+$", "", value)
    return value.rstrip("/").lower()


def set_text(item: ET.Element, tag: str, value) -> None:
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = str(value)


def coverage_nodes(item: ET.Element) -> list[ET.Element]:
    pool = item.findall("coveragePool/article")
    if pool:
        return pool
    related = item.findall("related/article")
    if related:
        return related
    return item.findall("relatedArticles/article")


def evidence(item: ET.Element, now: datetime):
    primary = source_key(item.findtext("source"))
    recent: dict[str, float] = {}
    historical: dict[str, float] = {}
    for node in coverage_nodes(item):
        src = source_key(node.findtext("source"))
        if not src or src == primary:
            continue
        dt = parse_date(node.findtext("pubDate"))
        if not dt:
            continue
        age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
        bucket = recent if age_days <= RECENT_WINDOW_DAYS else historical
        if src not in bucket or age_days < bucket[src]:
            bucket[src] = age_days

    # A publisher with both recent and old coverage is a recent supporting source,
    # not an additional historical source. This keeps historical metadata from
    # double-counting the same publisher while leaving eligibility/ranking unchanged.
    for src in recent:
        historical.pop(src, None)
    oldest_days = int(max(historical.values(), default=0))
    return recent, historical, oldest_days


def signal_for(count: int):
    if count == 1:
        return 58, "Possible underreported — limited corroboration", "low"
    if count == 2:
        return 88, "High underreporting signal", "high"
    if count == 3:
        return 84, "High underreporting signal", "high"
    if count == 4:
        return 80, "High underreporting signal", "high"
    if count == 5:
        return 68, "Moderate underreporting signal", "moderate"
    if count == 6:
        return 60, "Moderate underreporting signal", "moderate"
    if count == 7:
        return 52, "Underreporting signal weakening", "moderate"
    if count == 8:
        return 44, "Underreporting signal weakening", "moderate"
    return 0, "Insufficient/overbroad coverage evidence", "none"


def missing_text(recent_count: int, historical_count: int, oldest_days: int) -> str:
    if recent_count == 1:
        base = (
            "Only one independent approved supporting publisher was found in the last "
            f"{RECENT_WINDOW_DAYS} days. That is enough to flag this as a possible underreported issue, "
            "but not enough for a high-confidence underreporting claim."
        )
    elif 2 <= recent_count <= 4:
        base = (
            f"The story has {recent_count} independent approved supporting publishers in the last "
            f"{RECENT_WINDOW_DAYS} days. That limited but real corroboration is the strongest zone for "
            "an Underreported signal: the issue is verified without appearing broadly saturated."
        )
    else:
        base = (
            f"The story has {recent_count} independent approved supporting publishers in the last "
            f"{RECENT_WINDOW_DAYS} days. Coverage is broadening, so the Underreported signal is reduced."
        )
    if historical_count:
        base += (
            f" {historical_count} older approved source(s) were found outside the recent evidence window"
            + (f", reaching back about {oldest_days} days" if oldest_days else "")
            + "; those are treated as background only and do not increase the current supporting-source count."
        )
    return base


def main() -> None:
    tree = ET.parse(NEWS)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")
    now = datetime.now(timezone.utc)
    items = list(channel.findall("item"))
    under = [i for i in items if clean(i.findtext("category")).lower() == "underreported"]
    kept = []
    removed_zero = []
    removed_broad = []
    removed_duplicate = []
    histogram: dict[str, int] = {}
    seen_links: set[str] = set()
    seen_titles: set[str] = set()

    for item in under:
        title = clean(item.findtext("title"))
        link_key = canonical_link(item.findtext("link"))
        tkey = title_key(title)
        if (link_key and link_key in seen_links) or (tkey and tkey in seen_titles):
            removed_duplicate.append(title)
            continue

        recent, historical, oldest_days = evidence(item, now)
        count = len(recent)
        histogram[str(count)] = histogram.get(str(count), 0) + 1
        if count < MIN_RECENT_SOURCES:
            removed_zero.append(title)
            continue
        if count > MAX_RECENT_SOURCES:
            removed_broad.append(title)
            continue

        score, label, confidence = signal_for(count)
        set_text(item, "supportingSourceCount", count)
        set_text(item, "recentSupportingSourceCount", count)
        set_text(item, "historicalSupportingSourceCount", len(historical))
        set_text(item, "supportingEvidenceWindowDays", RECENT_WINDOW_DAYS)
        set_text(item, "oldestBackgroundAgeDays", oldest_days)
        set_text(item, "coverageGapScore", score)
        set_text(item, "underreportedScore", score)
        set_text(item, "coverage", label)
        set_text(item, "underreportedConfidence", confidence)
        set_text(item, "whatIsMissing", missing_text(count, len(historical), oldest_days))
        set_text(
            item,
            "signalMethod",
            "Underreported requires 1-8 distinct approved independent supporting publishers within the last "
            f"{RECENT_WINDOW_DAYS} days. Two to four recent sources is the highest-confidence zone. Older matches "
            "are background only; zero recent support is insufficient evidence and nine or more recent sources is "
            "treated as broadly covered."
        )
        try:
            old_priority = int(float(clean(item.findtext("underreportedPriority")) or 0))
        except Exception:
            old_priority = 0
        blended = round(old_priority * 0.55 + score * 0.45)
        if count == 1:
            blended = min(blended, 64)
        set_text(item, "underreportedPriority", max(0, min(100, blended)))
        kept.append(item)
        if link_key:
            seen_links.add(link_key)
        if tkey:
            seen_titles.add(tkey)

    def order_key(item: ET.Element):
        try: p = int(float(clean(item.findtext("underreportedPriority")) or 0))
        except Exception: p = 0
        try: s = int(float(clean(item.findtext("underreportedScore")) or 0))
        except Exception: s = 0
        dt = parse_date(item.findtext("pubDate"))
        return (p, s, dt.timestamp() if dt else 0)
    kept.sort(key=order_key, reverse=True)

    # Rebuild from the original direct channel items. Underreported cards are
    # replaced by the validated/deduped `kept` set exactly once. This avoids the
    # previous serialization bug where retained cards were appended again via rest.
    top = [i for i in items if clean(i.findtext("category")).lower() == "top"]
    rest = [i for i in items if clean(i.findtext("category")).lower() not in {"top", "underreported"}]
    for item in list(channel.findall("item")):
        channel.remove(item)
    for item in top + kept + rest:
        channel.append(item)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    report = {
        "policy": {
            "recentEvidenceWindowDays": RECENT_WINDOW_DAYS,
            "minimumRecentSupportingSources": MIN_RECENT_SOURCES,
            "maximumRecentSupportingSources": MAX_RECENT_SOURCES,
            "highConfidenceZone": "2-4 recent independent approved sources",
            "historicalCoverage": "background only; never counted as current support",
        },
        "before": len(under),
        "after": len(kept),
        "removedZeroRecentSupport": len(removed_zero),
        "removedBroadCoverage": len(removed_broad),
        "removedExactDuplicates": len(removed_duplicate),
        "recentSourceHistogramBeforeGuard": histogram,
        "removedZeroTitles": removed_zero[:30],
        "removedBroadTitles": removed_broad[:30],
        "removedDuplicateTitles": removed_duplicate[:30],
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
