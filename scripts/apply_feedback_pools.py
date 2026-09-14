#!/usr/bin/env python3
"""Apply persistent D/NR/NW feedback pools to the generated RSS feed.

D (Duplicate): suppresses the exact article identity globally.
NR (Not Relevant): suppresses the exact article identity in the recorded category.
NW (Not Wanted): suppresses the exact article identity in the recorded category.

The pool service is intentionally treated as authoritative in production. Use
--require-remote to fail instead of publishing without feedback enforcement.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

DEFAULT_API = "https://bkcrgfkhgjypvzwubwrh.supabase.co/functions/v1/news-feedback"
REASONS = ("D", "NR", "NW")


def normalize_text(value: str | None) -> str:
    text = (value or "").lower()
    text = re.sub(r"^\s*\d+[.)]\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        parts = urllib.parse.urlsplit(raw)
        if parts.scheme not in {"http", "https"}:
            return ""
        pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        drop = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}
        query = urllib.parse.urlencode([(k, v) for k, v in pairs if k not in drop])
        clean = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))
        return clean.rstrip("/").lower()
    except Exception:
        return raw.rstrip("/").lower()


def item_identity(item: ET.Element) -> dict[str, str]:
    title = (item.findtext("title") or "").strip()
    url = (item.findtext("link") or "").strip()
    source = (item.findtext("source") or "").strip()
    category = normalize_text(item.findtext("category"))
    return {
        "title": title,
        "title_key": normalize_text(title),
        "url": url,
        "url_key": normalize_url(url),
        "source": source,
        "source_key": normalize_text(source),
        "category": category,
    }


def pool_identity(record: dict[str, Any]) -> dict[str, str]:
    return {
        "title_key": normalize_text(record.get("title_key") or record.get("title")),
        "url_key": normalize_url(record.get("url_key") or record.get("url")),
        "source_key": normalize_text(record.get("source_key") or record.get("source")),
        "category": normalize_text(record.get("category")),
    }


def same_article(item: dict[str, str], record: dict[str, Any], *, require_category: bool) -> bool:
    r = pool_identity(record)
    if require_category and r["category"] and item["category"] != r["category"]:
        return False
    if r["url_key"] and item["url_key"] and r["url_key"] == item["url_key"]:
        return True
    return bool(
        r["title_key"]
        and r["title_key"] == item["title_key"]
        and r["source_key"] == item["source_key"]
    )


def matched_reason(item: dict[str, str], pools: dict[str, list[dict[str, Any]]]) -> str | None:
    for record in pools.get("D", []):
        if same_article(item, record, require_category=False):
            return "D"
    for reason in ("NR", "NW"):
        for record in pools.get(reason, []):
            if same_article(item, record, require_category=True):
                return reason
    return None


def fetch_pools(api_url: str, timeout: float = 15.0) -> dict[str, list[dict[str, Any]]]:
    request = urllib.request.Request(api_url, headers={"Accept": "application/json", "User-Agent": "underreported-feed/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"feedback API returned HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    raw = payload.get("pools") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        raise RuntimeError("feedback API payload has no pools object")
    pools: dict[str, list[dict[str, Any]]] = {reason: [] for reason in REASONS}
    for reason in REASONS:
        rows = raw.get(reason, [])
        if not isinstance(rows, list):
            raise RuntimeError(f"feedback pool {reason} is not a list")
        pools[reason] = [row for row in rows if isinstance(row, dict)]
    return pools


def apply_pools(feed_path: Path, pools: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tree = ET.parse(feed_path)
    root = tree.getroot()
    channel = root.find("channel") if root.tag.lower() == "rss" else None
    parent = channel if channel is not None else root
    items = list(parent.findall("item"))
    removed: list[dict[str, str]] = []
    for item in items:
        identity = item_identity(item)
        reason = matched_reason(identity, pools)
        if not reason:
            continue
        parent.remove(item)
        removed.append({
            "reason": reason,
            "category": identity["category"],
            "title": identity["title"],
            "url": identity["url"],
            "source": identity["source"],
        })
    if removed:
        try:
            ET.indent(tree, space="  ")
        except AttributeError:
            pass
        tree.write(feed_path, encoding="utf-8", xml_declaration=True)
    return {
        "poolCounts": {reason: len(pools.get(reason, [])) for reason in REASONS},
        "removedCount": len(removed),
        "removedByReason": {reason: sum(1 for row in removed if row["reason"] == reason) for reason in REASONS},
        "removed": removed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default="News")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--require-remote", action="store_true")
    parser.add_argument("--report", default="/tmp/feedback-pool-report.json")
    args = parser.parse_args()

    try:
        pools = fetch_pools(args.api)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        message = f"Feedback pool fetch failed: {exc}"
        if args.require_remote:
            print(message, file=sys.stderr)
            return 1
        print(message + "; continuing without feedback suppression.", file=sys.stderr)
        pools = {reason: [] for reason in REASONS}

    report = apply_pools(Path(args.feed), pools)
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Persistent feedback pools:", report["poolCounts"])
    print("Removed by feedback:", report["removedByReason"])
    if report["removed"]:
        for row in report["removed"][:20]:
            print(f"  [{row['reason']}] {row['category']}: {row['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
