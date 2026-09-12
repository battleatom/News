from __future__ import annotations

"""Build concise, complete factual briefs for news cards.

The script reads publicly returned article text, selects up to two useful facts,
paraphrases them into complete sentences, and never cuts a sentence with an
ellipsis. Headline, link, source, category, and ranking are left untouched.
"""
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4") from exc

try:
    from googlenewsdecoder import gnewsdecoder
except ImportError as exc:
    raise SystemExit("googlenewsdecoder is required: pip install googlenewsdecoder==0.1.7") from exc

NEWS = Path("News")
CACHE = Path("content-brief-cache.json")
CACHE_VERSION = 3
MIN_ARTICLE_TEXT = 180
FETCH_TIMEOUT = 9
FETCH_WORKERS = 8
CACHE_LIMIT = 1800
MAX_FACT_CHARS = 285
MAX_BRIEF_CHARS = 560
USER_AGENT = "Mozilla/5.0 (compatible; Underreported/4.0; +https://github.com/battleatom/News)"

BOILERPLATE = (
    "accept cookies", "cookie policy", "privacy policy", "terms of use", "sign up",
    "subscribe", "newsletter", "all rights reserved", "copyright", "advertisement",
    "read more", "continue reading", "download our app", "enable javascript",
    "report a missed paper", "e-edition", "customer service", "contact us",
    "posted by", "minute read", "min read", "outlets skipped it", "share this article",
    "follow us", "related stories", "recommended for you", "click here",
)

COMMON_REWRITES = (
    (r"\baccording to\b", "based on"),
    (r"\bsaid\b", "reported"),
    (r"\bsays\b", "reports"),
    (r"\bannounced\b", "outlined"),
    (r"\bannounces\b", "outlines"),
    (r"\bwill\b", "is expected to"),
    (r"\bamid\b", "during"),
    (r"\bhowever\b", "at the same time"),
    (r"\bmore than\b", "over"),
    (r"\bless than\b", "under"),
)


def clean(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, clean(a).lower(), clean(b).lower()).ratio()


def strip_source_suffix(text: str, source: str) -> str:
    out = clean(text)
    if source:
        out = re.sub(rf"\s*[-–—|:]\s*{re.escape(source)}\s*$", "", out, flags=re.I)
    return out.strip(" -–—|:")


def load_cache() -> dict[str, dict]:
    if not CACHE.exists():
        return {}
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(cache: dict[str, dict]) -> None:
    rows = sorted(cache.items(), key=lambda pair: str(pair[1].get("updatedAt", "")), reverse=True)[:CACHE_LIMIT]
    CACHE.write_text(json.dumps(dict(rows), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_google_news(url: str) -> bool:
    try:
        return urllib.parse.urlparse(url).hostname in {"news.google.com", "www.news.google.com"}
    except Exception:
        return False


def resolve_publisher_url(url: str) -> str:
    if not url:
        return ""
    if not is_google_news(url):
        return url
    try:
        result = gnewsdecoder(url)
        if isinstance(result, dict) and result.get("status"):
            decoded = clean(result.get("decoded_url"))
            if decoded.startswith(("http://", "https://")) and not is_google_news(decoded):
                return decoded
    except Exception:
        pass
    return ""


def text_is_clean(value: str, minimum: int = 80) -> bool:
    value = clean(value)
    low = value.lower()
    if len(value) < minimum or any(term in low for term in BOILERPLATE):
        return False
    if re.search(r"\b(?:https?://|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,})", value, re.I):
        return False
    return True


def best_jsonld_body(soup: BeautifulSoup) -> str:
    found: list[str] = []

    def walk(value) -> None:
        if isinstance(value, dict):
            body = value.get("articleBody")
            if isinstance(body, str) and text_is_clean(body, MIN_ARTICLE_TEXT):
                found.append(clean(body))
            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for node in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        try:
            raw = node.string or node.get_text(" ", strip=True)
            if raw:
                walk(json.loads(raw))
        except Exception:
            continue
    return max(found, key=len, default="")


def meta_text(soup: BeautifulSoup) -> str:
    selectors = (
        ('meta[property="og:description"]', "content"),
        ('meta[name="description"]', "content"),
        ('meta[name="twitter:description"]', "content"),
    )
    for selector, attr in selectors:
        node = soup.select_one(selector)
        value = clean(node.get(attr)) if node else ""
        if text_is_clean(value, 90):
            return value
    return ""


def paragraph_text(soup: BeautifulSoup) -> str:
    container = soup.find("article") or soup.find("main") or soup.body
    if not container:
        return ""
    paragraphs: list[str] = []
    for p in container.find_all("p"):
        text = clean(p.get_text(" ", strip=True))
        if not text_is_clean(text, 55):
            continue
        if re.match(r"^(?:i|i'm|i’ve|i'd|my|we|we're|we’ve|our)\b", text, re.I):
            continue
        if text.count("|") >= 2 or text.count("·") >= 2:
            continue
        if text not in paragraphs:
            paragraphs.append(text)
        if len(paragraphs) >= 16 or sum(len(x) for x in paragraphs) > 7500:
            break
    return " ".join(paragraphs)


def fetch_article(url: str) -> tuple[str, str, str]:
    publisher = resolve_publisher_url(url)
    if not publisher:
        return "", "", "unresolved"
    try:
        req = urllib.request.Request(
            publisher,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as response:
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                return publisher, "", "non-html"
            raw = response.read(900_000).decode("utf-8", "ignore")
        soup = BeautifulSoup(raw, "html.parser")
        meta = meta_text(soup)
        if meta:
            return publisher, meta, "article-meta"
        body = best_jsonld_body(soup)
        if len(body) >= MIN_ARTICLE_TEXT:
            return publisher, body, "article-body"
        body = paragraph_text(soup)
        if len(body) >= MIN_ARTICLE_TEXT:
            return publisher, body, "article-paragraphs"
        return publisher, "", "no-public-text"
    except Exception:
        return publisher, "", "fetch-blocked"


def split_sentences(text: str) -> list[str]:
    text = clean(text)
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])', text)
    out: list[str] = []
    for part in parts:
        part = clean(part).strip(" -–—")
        low = part.lower()
        if not 45 <= len(part) <= 520:
            continue
        if any(term in low for term in BOILERPLATE):
            continue
        if re.search(r"\b(?:https?://|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,})", part, re.I):
            continue
        if re.match(r"^(?:i|i'm|i’ve|i'd|my|we|we're|we’ve|our)\b", part, re.I):
            continue
        if part.count('"') >= 2 or "“" in part or "”" in part:
            continue
        if part.count("|") >= 2 or part.count("·") >= 2:
            continue
        if part not in out:
            out.append(part)
    return out


def title_terms(title: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "at", "from", "by", "as", "is", "are", "was", "were", "be", "after",
        "new", "says", "said", "will", "that", "this", "its", "their",
    }
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2 and w not in stop}


def sentence_score(sentence: str, title: str, position: int) -> float:
    terms = title_terms(title)
    words = set(re.findall(r"[a-z0-9]+", sentence.lower()))
    overlap = len(terms & words)
    numbers = min(2, len(re.findall(r"\b(?:\$?\d[\d,.]*%?|20\d{2})\b", sentence)))
    length_penalty = max(0, (len(sentence) - 260) / 55)
    return overlap * 4 + numbers * 1.5 + max(0, 6 - position * 0.45) - length_penalty


def simplify_attribution(sentence: str) -> str:
    s = clean(sentence)
    s = re.sub(r"^(?:breaking:?\s*|exclusive:?\s*|update:?\s*)", "", s, flags=re.I)
    s = re.sub(r"^(?:in a statement,?\s*|the report said(?: that)?\s*)", "", s, flags=re.I)
    for pattern, replacement in COMMON_REWRITES:
        s = re.sub(pattern, replacement, s, flags=re.I)
    return s.strip().rstrip(" .")


def complete_clause(sentence: str, limit: int = MAX_FACT_CHARS) -> str:
    """Shorten only at a grammatical clause boundary; never use an ellipsis."""
    s = simplify_attribution(sentence)
    s = re.sub(r"^\s*[A-Z][A-Z .,'-]{2,25}\s*[-—:]\s*", "", s)
    s = re.sub(r"\s*\([^)]{1,120}\)\s*", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,;:-")
    if not s:
        return ""
    if len(s) <= limit:
        return s
    split_patterns = (
        r"\s+[—–-]\s+",
        r";\s+",
        r",\s+(?=(?:which|who|while|although|though|because|after|before|as|with|including|according to)\b)",
    )
    for pattern in split_patterns:
        first = re.split(pattern, s, maxsplit=1, flags=re.I)[0].strip(" ,;:-")
        if 85 <= len(first) <= limit and re.search(r"\b(?:is|are|was|were|has|have|had|will|can|could|may|might|plans?|launched?|released?|reported|outlined|raised?|cut|delayed?|won|lost|filed|joined|signed|acquired|approved|rejected|announced)\b", first, re.I):
            return first
    return ""


def choose_facts(article_text: str, title: str) -> list[str]:
    candidates = split_sentences(article_text)[:26]
    ranked = sorted(enumerate(candidates), key=lambda pair: sentence_score(pair[1], title, pair[0]), reverse=True)
    selected: list[tuple[int, str]] = []
    for pos, sentence_value in ranked:
        shortened = complete_clause(sentence_value)
        if not shortened:
            continue
        if similarity(shortened, title) > 0.93:
            continue
        if any(similarity(shortened, prior) > 0.72 for _, prior in selected):
            continue
        selected.append((pos, shortened))
        if len(selected) == 2:
            break
    selected.sort(key=lambda pair: pair[0])
    return [sentence_value for _, sentence_value in selected]


def sentence(text: str) -> str:
    value = clean(text).rstrip(" .!?")
    if not value:
        return ""
    if value[0].islower():
        value = value[0].upper() + value[1:]
    return value + "."


def build_brief(title: str, source_text: str, source: str, category: str) -> str:
    title = strip_source_suffix(title, source)
    facts = choose_facts(source_text, title)
    if not facts:
        return ""
    first = sentence(facts[0])
    second = sentence(facts[1]) if len(facts) > 1 else ""
    brief = " ".join(x for x in (first, second) if x)
    if len(brief) > MAX_BRIEF_CHARS and second:
        brief = first
    return brief


def set_text(item: ET.Element, tag: str, value: str) -> None:
    el = item.find(tag)
    if el is None:
        el = ET.SubElement(item, tag)
    el.text = value


def fallback_brief(row: dict[str, str]) -> str:
    title = strip_source_suffix(row["title"], row["source"]).rstrip(" .")
    return (
        f"This story centers on {title}. "
        "The publisher did not expose enough public article text for a fuller verified brief."
    )


def process_row(index: int, row: dict[str, str], cached: dict | None) -> tuple[int, dict]:
    if cached and cached.get("cacheVersion") == CACHE_VERSION and cached.get("brief"):
        brief = clean(cached.get("brief"))
        if len(brief) >= 60 and "…" not in brief:
            return index, cached
    publisher, article_text, kind = fetch_article(row["link"])
    brief = build_brief(row["title"], article_text, row["source"], row["category"]) if article_text else ""
    if not brief:
        brief = fallback_brief(row)
        kind = "headline-fallback"
    return index, {
        "cacheVersion": CACHE_VERSION,
        "brief": brief,
        "publisherUrl": publisher,
        "sourceKind": kind,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    if not NEWS.exists():
        raise SystemExit("News feed not found")
    tree = ET.parse(NEWS)
    root = tree.getroot()
    items = list(root.findall(".//item"))
    if not items:
        raise SystemExit("News feed contains no items")

    cache = load_cache()
    rows: list[dict[str, str]] = []
    for item in items:
        rows.append({
            "title": clean(item.findtext("title")),
            "description": clean(item.findtext("description")),
            "link": clean(item.findtext("link")),
            "source": clean(item.findtext("source")),
            "category": clean(item.findtext("category")).lower(),
        })

    results: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {
            pool.submit(process_row, i, row, cache.get(row["link"])): i
            for i, row in enumerate(rows)
        }
        for future in as_completed(futures):
            i = futures[future]
            try:
                _, result = future.result()
            except Exception:
                result = {
                    "cacheVersion": CACHE_VERSION,
                    "brief": fallback_brief(rows[i]),
                    "publisherUrl": "",
                    "sourceKind": "headline-fallback",
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                }
            results[i] = result

    counts: dict[str, int] = {}
    for i, (item, row) in enumerate(zip(items, rows)):
        result = results[i]
        brief = clean(result.get("brief"))
        kind = clean(result.get("sourceKind")) or "unknown"
        set_text(item, "description", brief)
        set_text(item, "briefGenerated", "true")
        set_text(item, "briefSource", kind)
        if result.get("publisherUrl"):
            set_text(item, "resolvedPublisherUrl", clean(result["publisherUrl"]))
        counts[kind] = counts.get(kind, 0) + 1
        cache[row["link"]] = result

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    save_cache(cache)
    useful = sum(v for k, v in counts.items() if k != "headline-fallback")
    detail = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"Content briefs: {len(items)}/{len(items)} generated; article-backed={useful}; {detail}")


if __name__ == "__main__":
    main()
