from pathlib import Path
import html
import re
import urllib.request
import xml.etree.ElementTree as ET

NEWS = Path("News")

SOURCE_SUFFIXES = {
    "AP News", "Associated Press", "Reuters", "BBC", "CNN", "Fox News",
    "NBC News", "ABC News", "CBS News", "NPR", "USA Today",
    "The New York Times", "The Washington Post", "WV News"
}

GENERIC_PATTERNS = [
    re.compile(r"^trump\s*[-–—|:]\s*(?:wv news|news)$", re.I),
    re.compile(r"^[a-z][a-z .'-]{0,30}\s*[-–—|:]\s*(?:wv news|news)$", re.I),
]


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def strip_source(title, source):
    title = clean(title)
    for suffix in [source] + list(SOURCE_SUFFIXES):
        if suffix:
            title = re.sub(rf"\s*[-–—|:]\s*{re.escape(suffix)}\s*$", "", title, flags=re.I)
    return title.strip(" -–—|:")


def fetch_description(url):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 Underreported/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read(500_000).decode("utf-8", "ignore")
        patterns = [
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, raw, flags=re.I | re.S)
            if match:
                value = clean(match.group(1))
                if len(value) >= 60:
                    return value
    except Exception:
        pass
    return ""


def main():
    if not NEWS.exists():
        raise SystemExit("News feed not found")

    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    removed = 0
    enriched = 0
    for item in list(channel.findall("item")):
        category = clean(item.findtext("category"))
        if category != "world":
            continue

        title_el = item.find("title")
        desc_el = item.find("description")
        source = clean(item.findtext("source"))
        title = clean(title_el.text if title_el is not None else "")
        cleaned_title = strip_source(title, source)
        if title_el is not None:
            title_el.text = cleaned_title

        description = clean(desc_el.text if desc_el is not None else "")
        description = strip_source(description, source)

        # Google News sometimes returns a publisher label instead of actual
        # article content. Try the resolved article page for a real summary.
        link = clean(item.findtext("link"))
        if not description or description.lower() == cleaned_title.lower() or len(description) < 60:
            fetched = fetch_description(link) if link else ""
            if fetched and fetched.lower() != cleaned_title.lower():
                description = fetched
                enriched += 1

        # Do not publish vague/source-branded headlines as World news.
        words = re.findall(r"[A-Za-z0-9']+", cleaned_title)
        generic = any(pattern.search(title) for pattern in GENERIC_PATTERNS)
        if generic or len(words) < 4:
            channel.remove(item)
            removed += 1
            continue

        if desc_el is not None:
            desc_el.text = description

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"World content enrichment complete: {enriched} summaries added, {removed} vague stories removed.")


if __name__ == "__main__":
    main()
