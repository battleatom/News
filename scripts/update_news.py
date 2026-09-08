import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

OUT = "News"
SECTIONS = ["top", "world", "us", "presidential", "federal", "nm", "local", "technology", "military"]
MAX_AGE_HOURS = 72

QUERIES = {
    "world": "world news OR international news",
    "us": "United States news OR US politics",
    "presidential": "Trump president White House",
    "federal": "US Congress OR federal government OR Supreme Court",
    "nm": "New Mexico government OR New Mexico news",
    "local": "Farmington New Mexico OR Four Corners New Mexico",
    "technology": "technology AI cybersecurity science",
    "military": "military war conflict Pentagon NATO",
}


def feed_url(query):
    # Restrict Google News search to recent coverage. The RSS endpoint can otherwise
    # return old articles when a search term has little current coverage.
    q = urllib.parse.quote(f"{query} when:3d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value):
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def fetch(query):
    req = urllib.request.Request(
        feed_url(query),
        headers={"User-Agent": "Mozilla/5.0 NewsBrief/1.1"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read())


def parse_items(root, category):
    result = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)

    for item in root.findall(".//item"):
        title = clean(item.findtext("title"))
        link = item.findtext("link") or ""
        desc = clean(item.findtext("description"))
        pub = item.findtext("pubDate") or ""
        published = parse_date(pub)
        source_el = item.find("source")
        source = clean(source_el.text if source_el is not None else "")

        if not title or not link or not published:
            continue
        if published < cutoff or published > now + timedelta(minutes=10):
            continue

        result.append({
            "title": title,
            "link": link,
            "description": desc,
            "pubDate": pub,
            "published": published,
            "source": source,
            "category": category,
        })

    return result


def key(item):
    words = re.findall(r"[a-z0-9]+", item["title"].lower())
    stop = {
        "the", "a", "an", "to", "of", "in", "on", "for", "and", "with",
        "is", "as", "at", "from", "by", "after", "new", "says"
    }
    return " ".join(w for w in words if w not in stop)[:180]


def xml_escape(value):
    return html.escape(value or "", quote=False)


def build(items):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        '<title>News Brief</title>',
        '<link>https://battleatom.github.io/News/</link>',
        '<description>Automated categorized news brief</description>',
        f'<lastBuildDate>{now}</lastBuildDate>',
    ]
    for item in items:
        # Stable GUIDs are important because Python's built-in hash changes between runs.
        guid = urllib.parse.quote(item["link"], safe="")[:240]
        out += [
            "<item>",
            f'<title>{xml_escape(item["title"])}</title>',
            f'<link>{xml_escape(item["link"])}</link>',
            f'<description>{xml_escape(item["description"])}</description>',
            f'<pubDate>{xml_escape(item["pubDate"])}</pubDate>',
            f'<source>{xml_escape(item["source"])}</source>',
            f'<category>{item["category"]}</category>',
            f'<guid isPermaLink="false">{xml_escape(guid)}</guid>',
            "</item>",
        ]
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


def main():
    all_items = []
    for category, query in QUERIES.items():
        try:
            items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories")
            all_items.extend(items)
        except Exception as exc:
            print(f"Feed failed for {category}: {exc}")

    # Remove duplicate stories, keeping the first category/source assignment.
    seen = set()
    unique = []
    for item in sorted(all_items, key=lambda x: x["published"], reverse=True):
        k = key(item)
        if not k or k in seen:
            continue
        seen.add(k)
        unique.append(item)

    # Select the freshest 10 stories for each requested section.
    selected_by_category = {}
    for category in SECTIONS[1:]:
        selected_by_category[category] = [
            x for x in unique if x["category"] == category
        ][:10]

    # Top Stories is the freshest set across every category.
    top = unique[:10]

    ordered = top[:]
    for category in SECTIONS[1:]:
        for item in selected_by_category[category]:
            if item not in ordered:
                ordered.append(item)

    if not ordered:
        raise RuntimeError("No fresh stories were retrieved; refusing to overwrite News with an empty feed.")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(ordered))
    print(f"Wrote {len(ordered)} fresh stories to {OUT}")


if __name__ == "__main__":
    main()
