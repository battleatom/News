from __future__ import annotations

"""Create short, original factual briefs for every news card.

This runs after collection/ranking/deduplication and before the HTML build. It keeps
headlines, links, sources, categories and ranking untouched. The existing RSS/meta
summary is used as factual input, then rewritten into a compact digest. When the
feed summary is too weak, the script makes a best-effort request for the public
article page's meta description. It does not bypass logins, paywalls or robots.
"""

import html
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path

NEWS = Path("News")
MAX_BRIEF_CHARS = 430
MIN_USEFUL_DESCRIPTION = 90
FETCH_TIMEOUT = 6
FETCH_WORKERS = 10
USER_AGENT = "Mozilla/5.0 Underreported/3.0 (+news briefing preview)"

CATEGORY_OPENERS = {
    "world": "International reporting indicates",
    "us": "U.S. reporting indicates",
    "presidential": "White House coverage indicates",
    "federal": "Federal coverage indicates",
    "legislation": "Legislative coverage indicates",
    "nm": "New Mexico reporting indicates",
    "local": "Local reporting indicates",
    "region": "Regional reporting indicates",
    "nfl": "NFL coverage indicates",
    "technology": "Technology reporting indicates",
    "gaming": "Gaming coverage indicates",
    "military": "Defense reporting indicates",
    "underreported": "Reporting on this issue indicates",
}

REPLACEMENTS = (
    (r"\baccording to\b", "as reported by"),
    (r"\bsaid\b", "reported"),
    (r"\bsays\b", "reports"),
    (r"\bannounced\b", "reported plans for"),
    (r"\bannounces\b", "reports plans for"),
    (r"\bwill\b", "is set to"),
    (r"\bafter\b", "following"),
    (r"\bamid\b", "during"),
    (r"\bbut\b", "while"),
    (r"\bhowever\b", "at the same time"),
    (r"\bmore than\b", "over"),
    (r"\bless than\b", "under"),
)

BOILERPLATE = (
    "click here", "read more", "continue reading", "sign up", "newsletter",
    "all rights reserved", "copyright", "watch live", "advertisement",
)


def clean(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def strip_source_suffix(text: str, source: str) -> str:
    out = clean(text)
    if source:
        out = re.sub(rf"\s*[-–—|:]\s*{re.escape(source)}\s*$", "", out, flags=re.I)
    return out.strip(" -–—|:")


def sentences(text: str) -> list[str]:
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text)
    out: list[str] = []
    for part in parts:
        part = part.strip(" \t\r\n-–—")
        if len(part) < 28:
            continue
        low = part.lower()
        if any(x in low for x in BOILERPLATE):
            continue
        if part not in out:
            out.append(part)
    return out


def meta_description(url: str) -> str:
    if not url or not url.startswith(("http://", "https://")):
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as response:
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                return ""
            raw = response.read(350_000).decode("utf-8", "ignore")
        patterns = (
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
        )
        for pattern in patterns:
            match = re.search(pattern, raw, flags=re.I | re.S)
            if match:
                value = clean(match.group(1))
                if len(value) >= MIN_USEFUL_DESCRIPTION:
                    return value
    except Exception:
        return ""
    return ""


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, clean(a).lower(), clean(b).lower()).ratio()


def rewrite_sentence(sentence: str) -> str:
    s = clean(sentence)
    # Remove common publisher-style lead-ins and promotional framing.
    s = re.sub(r"^(?:breaking:?\s*|exclusive:?\s*|update:?\s*)", "", s, flags=re.I)
    s = re.sub(r"^(?:in a statement,?\s*|officials? said(?: that)?\s*|the report said(?: that)?\s*)", "", s, flags=re.I)
    for pattern, replacement in REPLACEMENTS:
        s = re.sub(pattern, replacement, s, flags=re.I)
    # Prefer a neutral factual tone over article-copy phrasing.
    s = re.sub(r"\bwe\b", "the outlet", s, flags=re.I)
    s = re.sub(r"\bour\b", "the outlet's", s, flags=re.I)
    s = s.strip()
    if s:
        s = s[0].lower() + s[1:] if len(s) > 1 and s[0].isupper() else s
    return s.rstrip(" .")


def trim(text: str, limit: int = MAX_BRIEF_CHARS) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    stop = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(", "))
    if stop >= int(limit * 0.65):
        return cut[: stop + 1].rstrip()
    stop = cut.rfind(" ")
    return (cut[:stop] if stop > 0 else cut[:limit]).rstrip(" ,;:") + "…"


def build_brief(title: str, description: str, source: str, category: str) -> str:
    title = strip_source_suffix(title, source)
    description = strip_source_suffix(description, source)
    candidates = sentences(description)

    useful: list[str] = []
    for sentence in candidates:
        if similarity(sentence, title) > 0.88:
            continue
        rewritten = rewrite_sentence(sentence)
        if len(rewritten) < 24:
            continue
        if rewritten not in useful:
            useful.append(rewritten)
        if len(useful) >= 2:
            break

    opener = CATEGORY_OPENERS.get(category, "Reporting indicates")
    if useful:
        first = useful[0]
        brief = f"{opener} {first}."
        if len(useful) > 1:
            second = useful[1]
            # A second sentence gives the card actual substance without recreating the article.
            brief += f" The source also reports that {second}."
    else:
        # Last-resort fallback still makes clear this is a digest, not copied article text.
        topic = title.rstrip(" .")
        brief = f"{opener} a developing story involving {topic}. Open the original report for the full details."

    # Avoid accidental near-verbatim output when a source description is only one sentence.
    if description and similarity(brief, description) > 0.86:
        brief = f"{opener} new details about {title.rstrip(' .')}. The available source summary points to {rewrite_sentence(description)}."
    return trim(brief)


def set_text(item: ET.Element, tag: str, value: str) -> None:
    el = item.find(tag)
    if el is None:
        el = ET.SubElement(item, tag)
    el.text = value


def main() -> None:
    if not NEWS.exists():
        raise SystemExit("News feed not found")

    tree = ET.parse(NEWS)
    root = tree.getroot()
    items = list(root.findall(".//item"))
    if not items:
        raise SystemExit("News feed contains no items")

    weak: list[tuple[int, str]] = []
    rows: list[dict[str, str]] = []
    for i, item in enumerate(items):
        row = {
            "title": clean(item.findtext("title")),
            "description": clean(item.findtext("description")),
            "link": clean(item.findtext("link")),
            "source": clean(item.findtext("source")),
            "category": clean(item.findtext("category")).lower(),
        }
        rows.append(row)
        desc = row["description"]
        if len(desc) < MIN_USEFUL_DESCRIPTION or similarity(desc, row["title"]) > 0.82:
            weak.append((i, row["link"]))

    # Only weak/missing summaries cause an article-page request. This keeps refreshes fast
    # and avoids unnecessary scraping while still giving every card a usable brief.
    fetched: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {pool.submit(meta_description, url): idx for idx, url in weak if url}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                value = future.result()
            except Exception:
                value = ""
            if value:
                fetched[idx] = value

    generated = 0
    page_enriched = 0
    fallbacks = 0
    for i, (item, row) in enumerate(zip(items, rows)):
        source_text = fetched.get(i) or row["description"]
        if i in fetched:
            page_enriched += 1
        brief = build_brief(row["title"], source_text, row["source"], row["category"])
        if "Open the original report for the full details." in brief:
            fallbacks += 1
        set_text(item, "description", brief)
        set_text(item, "briefGenerated", "true")
        set_text(item, "briefSource", "page-meta" if i in fetched else "feed-summary")
        generated += 1

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(
        f"Content briefs generated: {generated}/{len(items)}; "
        f"page-meta enrichments: {page_enriched}; title-only fallbacks: {fallbacks}."
    )


if __name__ == "__main__":
    main()
