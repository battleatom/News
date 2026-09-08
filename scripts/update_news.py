import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

OUT = "News"
SECTIONS = ["top", "world", "us", "presidential", "federal", "nm", "local", "technology", "military"]

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
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch(query):
    req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 NewsBrief/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read())


def parse_items(root, category):
    result = []
    for item in root.findall(".//item"):
        title = clean(item.findtext("title"))
        link = item.findtext("link") or ""
        desc = clean(item.findtext("description"))
        pub = item.findtext("pubDate") or ""
        source_el = item.find("source")
        source = clean(source_el.text if source_el is not None else "")
        if not title or not link:
            continue
        result.append({"title": title, "link": link, "description": desc, "pubDate": pub, "source": source, "category": category})
    return result


def key(item):
    words = re.findall(r"[a-z0-9]+", item["title"].lower())
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at"}
    return " ".join(w for w in words if w not in stop)[:180]


def xml_escape(value):
    return html.escape(value or "", quote=False)


def build(items):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>', '<title>News Brief</title>', '<link>https://battleatom.github.io/News/</link>', '<description>Automated categorized news brief</description>', f'<lastBuildDate>{now}</lastBuildDate>']
    for item in items:
        out += ["<item>", f'<title>{xml_escape(item["title"])}</title>', f'<link>{xml_escape(item["link"])}</link>', f'<description>{xml_escape(item["description"])}</description>', f'<pubDate>{xml_escape(item["pubDate"])}</pubDate>', f'<source>{xml_escape(item["source"])}</source>', f'<category>{item["category"]}</category>', f'<guid isPermaLink="false">{abs(hash(item["link"]))}</guid>', "</item>"]
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


def main():
    all_items = []
    for category, query in QUERIES.items():
        try:
            all_items.extend(parse_items(fetch(query), category))
        except Exception as exc:
            print(f"Feed failed for {category}: {exc}")

    # Remove duplicate stories, favoring the first source returned.
    seen = set()
    unique = []
    for item in all_items:
        k = key(item)
        if k in seen:
            continue
        seen.add(k)
        unique.append(item)

    # Up to 10 per requested section; top stories are the newest across all categories.
    selected = []
    for category in SECTIONS[1:]:
        selected.extend([x for x in unique if x["category"] == category][:10])
    top = sorted(unique, key=lambda x: x["pubDate"], reverse=True)[:10]
    for item in top:
        if item not in selected:
            selected.insert(0, item)
    # Keep top items first, followed by categorized sections.
    ordered = top + [x for x in selected if x not in top]

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(ordered))
    print(f"Wrote {len(ordered)} stories to {OUT}")


if __name__ == "__main__":
    main()
