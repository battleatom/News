from pathlib import Path
from datetime import datetime, timezone
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

NEWS = Path("News")
MAX_AGE_DAYS = 2

CATEGORIES = [
    ("Health", "health medical disease FDA public health"),
    ("Technology & AI", "AI technology OpenAI Google Apple cybersecurity"),
    ("Celebrities & Public Figures", "celebrity actor singer athlete public figure"),
    ("World", "world international conflict war diplomacy"),
    ("Politics & Government", "Trump White House Congress Supreme Court politics"),
    ("Entertainment", "movies music television streaming entertainment"),
    ("Sports", "NFL NBA MLB soccer sports"),
    ("Business & Economy", "economy stocks tariffs jobs business companies"),
    ("Gaming", "gaming PlayStation Xbox Nintendo PC games"),
    ("Science", "science space NASA climate research"),
    ("Internet Culture", "internet culture memes creators social media"),
    ("Breaking / Emerging", "breaking developing viral emerging news"),
]

STOP = {"the","a","an","to","of","in","on","for","and","with","is","as","at","from","by","after","new","says","said","that","this","are","was","were","has","have","had","into","over","its","their","will","news","latest","x","twitter","post","posts"}
GENERIC = {"trump", "elon musk", "donald trump", "taylor swift", "kim kardashian", "celebrity", "breaking news", "viral", "x", "twitter"}


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 4 and w not in STOP}


def date(value):
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        return None


def fetch(query, days=2):
    q = urllib.parse.quote(f"{query} when:{days}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Underreported-X/2.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return ET.fromstring(response.read())


def is_x_activity(item):
    title = clean(item.findtext("title")); desc = clean(item.findtext("description")); link = clean(item.findtext("link"))
    text = f"{title} {desc}".lower()
    return "x.com/" in link.lower() or "twitter.com/" in link.lower() or bool(re.search(r"\b(?:on|posted on|posts? on|from)\s+(?:x|twitter)\b", text))


def usable_x_title(title):
    t = clean(title)
    low = t.lower().strip(" .:-—–")
    if len(words(t)) < 3:
        return False
    if low in GENERIC:
        return False
    if re.fullmatch(r"[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,2}", t):
        return False
    return len(t) >= 28


def news_item_data(item):
    source_el = item.find("source")
    return {
        "title": clean(item.findtext("title")),
        "link": clean(item.findtext("link")),
        "desc": clean(item.findtext("description")),
        "pub": clean(item.findtext("pubDate")),
        "source": clean(source_el.text if source_el is not None else ""),
        "dt": date(item.findtext("pubDate")),
    }


def best_x_signal(query):
    try:
        rss = fetch(f"site:x.com {query} (trending OR viral OR discussion OR controversy)")
    except Exception:
        return None
    candidates = []
    for item in rss.findall(".//item"):
        data = news_item_data(item)
        if not data["dt"] or not data["title"] or not is_x_activity(item) or not usable_x_title(data["title"]):
            continue
        candidates.append(data)
    return max(candidates, key=lambda x: x["dt"], default=None)


def supporting_reporting(signal, query):
    # Search the underlying event without forcing X. This turns an X conversation
    # into an explainable news issue instead of repeating the X post headline.
    terms = list(words(signal["title"]))[:10]
    search = " ".join(terms) or query
    try:
        rss = fetch(search, days=MAX_AGE_DAYS)
    except Exception:
        return []
    results = []
    for item in rss.findall(".//item"):
        data = news_item_data(item)
        if not data["dt"] or not data["title"]:
            continue
        if "x.com/" in data["link"].lower() or "twitter.com/" in data["link"].lower():
            continue
        overlap = len(words(data["title"]) & words(signal["title"]))
        if overlap >= 2:
            results.append((overlap, data))
    results.sort(key=lambda x: (x[0], x[1]["dt"]), reverse=True)
    return [x[1] for x in results[:4]]


def make_summary(signal, reports):
    if not reports:
        return "Publicly indexed X activity is drawing attention to this topic, but there is not enough independent reporting to explain the underlying event confidently."
    descs = [r["desc"] for r in reports if len(r["desc"]) > 60]
    if descs:
        return descs[0]
    return "Independent reporting is developing around the issue being discussed on X. See the supporting coverage below for the verified context."


def main():
    if not NEWS.exists():
        raise SystemExit("News feed not found")
    tree = ET.parse(NEWS)
    root = tree.getroot(); channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    for item in list(channel.findall("item")):
        if clean(item.findtext("category")) == "x":
            channel.remove(item)

    created = 0
    for category, query in CATEGORIES:
        signal = best_x_signal(query)
        if not signal:
            continue
        reports = supporting_reporting(signal, query)
        if not reports:
            # Do not publish a bare X post as a news story.
            continue

        lead = reports[0]
        issue = ET.Element("item")
        ET.SubElement(issue, "title").text = lead["title"]
        ET.SubElement(issue, "link").text = lead["link"]
        ET.SubElement(issue, "description").text = make_summary(signal, reports)
        ET.SubElement(issue, "pubDate").text = lead["pub"]
        ET.SubElement(issue, "source").text = lead["source"] or "Independent reporting"
        ET.SubElement(issue, "category").text = "x"
        ET.SubElement(issue, "xTopic").text = category
        ET.SubElement(issue, "xSignal").text = "Top indexed X conversation"
        ET.SubElement(issue, "xWhyTrending").text = f"Publicly indexed X activity is converging on this issue; the strongest signal is the discussion represented by: {signal['title']}"
        ET.SubElement(issue, "xWhatPeopleAreSaying").text = "X discussion is summarized here as conversation, not fact. Different users may be reacting to the same event from very different perspectives."
        ET.SubElement(issue, "xConfirmed").text = "The underlying event is supported by independent reporting linked below. The existence or intensity of the X conversation is separate from whether individual claims are true."
        ET.SubElement(issue, "xUnconfirmed").text = "Individual claims, rumors, screenshots, and interpretations circulating on X should be treated as unverified unless confirmed by a reliable source or primary documentation."
        rel = ET.SubElement(issue, "xRelated")
        seen = set()
        for r in reports:
            if r["link"] in seen: continue
            seen.add(r["link"])
            child = ET.SubElement(rel, "article")
            ET.SubElement(child, "title").text = r["title"]
            ET.SubElement(child, "link").text = r["link"]
            ET.SubElement(child, "source").text = r["source"]
            ET.SubElement(child, "pubDate").text = r["pub"]
        channel.append(issue)
        created += 1

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"X Top Issues: created {created} category leaders; skipped categories without enough independent reporting.")


if __name__ == "__main__":
    main()
