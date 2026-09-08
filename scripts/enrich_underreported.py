from pathlib import Path
from datetime import datetime, timezone
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NEWS = Path("News")
MAX_RELATED = 4


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def words(text):
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by", "after", "new", "says", "said", "that", "this", "are", "was", "were", "has", "have", "had", "into", "over", "its", "their", "will"}
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 4 and w not in stop}


def feed_url(query):
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def fetch_related(title):
    query_words = [w for w in re.findall(r"[A-Za-z0-9]+", title) if len(w) > 3]
    query = " ".join(query_words[:14])
    if not query:
        return []
    try:
        req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 Underreported/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            root = ET.fromstring(response.read())
    except Exception:
        return []

    target = words(title)
    candidates = []
    now = datetime.now(timezone.utc)
    for item in root.findall(".//item"):
        t = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        desc = clean(item.findtext("description"))
        pub = clean(item.findtext("pubDate"))
        source_el = item.find("source")
        source = clean(source_el.text if source_el is not None else "")
        if not t or not link or t.lower() == title.lower():
            continue
        overlap = len(target & words(t))
        if overlap < 2:
            continue
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except Exception:
            dt = None
        age_bonus = 0
        if dt:
            age_days = max(0, (now - dt).days)
            # Prefer useful history, but allow older supporting reporting.
            age_bonus = min(8, age_days / 30)
        score = overlap * 10 + age_bonus
        candidates.append((score, dt or datetime.min.replace(tzinfo=timezone.utc), t, link, desc, source, pub))

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected = []
    seen_sources = set()
    for row in candidates:
        source_key = re.sub(r"[^a-z0-9]", "", row[5].lower()) or row[3]
        if source_key in seen_sources and len(selected) < 2:
            continue
        selected.append(row)
        seen_sources.add(source_key)
        if len(selected) >= MAX_RELATED:
            break
    return selected


def specific_why(title, desc, category):
    text = f"{title} {desc}".lower()
    if any(x in text for x in ("attack", "airstrike", "missile", "invasion", "troops", "war", "ceasefire")):
        return "The significance is tied to a change in the security situation, military activity, or diplomatic position described in the reporting."
    if any(x in text for x in ("court", "ruling", "lawsuit", "supreme court", "executive order")):
        return "The significance is tied to the legal or government decision described here and the precedent, policy, or rights it may affect."
    if any(x in text for x in ("congress", "senate", "house", "bill", "vote", "legislation")):
        return "The significance is tied to the government action or legislative step described here, including what it could change next."
    if any(x in text for x in ("tariff", "inflation", "recession", "layoffs", "bankruptcy", "price")):
        return "The significance is tied to the economic change described here and its potential effect on businesses, workers, prices, or consumers."
    if any(x in text for x in ("hack", "breach", "cyberattack", "outage", "data leak")):
        return "The significance is tied to the affected system, organization, or users described in the reporting and what happens as the response develops."
    if any(x in text for x in ("wildfire", "hurricane", "tornado", "earthquake", "drought", "flood", "contamination")):
        return "The significance is tied to the people, infrastructure, or resources affected by the event and the response that follows."
    if any(x in text for x in ("acquisition", "acquires", "studio closure", "shuts down", "canceled", "cancelled")):
        return "The significance is tied to the organizational change described here and what it means for the people, products, or services involved."
    if category == "military":
        return "The significance is tied to the defense or security development described in the reporting and whether it changes the situation going forward."
    return "The significance comes from the specific action or development described in the reporting and what it may lead to next."


def what_next(desc, related):
    sentences = re.split(r"(?<=[.!?])\s+", desc or "")
    cues = ("will ", "plans to", "expected", "scheduled", "deadline", "next", "later", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "vote", "hearing", "trial", "meeting", "announce")
    matches = [s.strip() for s in sentences if any(c in s.lower() for c in cues) and len(s.strip()) >= 35]
    if matches:
        return matches[0]
    if related:
        return "No specific next step was stated in the available current report. The related coverage below provides earlier or additional reporting to track what happens next."
    return "No specific next step was stated in the available current report."


def replace_children(parent, tag):
    for child in list(parent.findall(tag)):
        parent.remove(child)


def main():
    if not NEWS.exists():
        raise SystemExit("News feed not found")
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    enriched = 0
    for item in channel.findall("item"):
        if clean(item.findtext("category")) != "underreported":
            continue
        title = clean(item.findtext("title"))
        desc = clean(item.findtext("description"))
        category = clean(item.findtext("category"))
        related = fetch_related(title)

        fields = {
            "whatHappened": desc if len(desc) >= 40 else f"The available report identifies this development: {title}.",
            "whyMatters": specific_why(title, desc, category),
            "whatIsMissing": (f"This story appears in limited coverage: {len(related) + 1} related report(s) were found across the available search results, compared with the broader volume of routine news." if related else "Limited supporting coverage was found in the available search results. That makes the story worth watching rather than assuming the coverage is complete."),
            "background": (f"Earlier or additional reporting is available below. These supporting links are intentionally searched without the site's 48-hour cutoff so developing stories can retain their history." if related else "No reliable older supporting report was identified from the available search results."),
            "whatNext": what_next(desc, related),
            "coverage": ("🟢 Overlooked" if len(related) == 0 else "🟡 Limited coverage"),
        }
        for tag, value in fields.items():
            el = item.find(tag)
            if el is None:
                el = ET.SubElement(item, tag)
            el.text = value

        replace_children(item, "related")
        if related:
            rel = ET.SubElement(item, "related")
            for _, dt, t, link, rd, source, pub in related:
                r = ET.SubElement(rel, "article")
                ET.SubElement(r, "title").text = t
                ET.SubElement(r, "link").text = link
                ET.SubElement(r, "description").text = rd
                ET.SubElement(r, "source").text = source
                ET.SubElement(r, "pubDate").text = pub
        enriched += 1

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Underreported enrichment complete: {enriched} stories enriched with story-specific context and longer-term supporting coverage.")


if __name__ == "__main__":
    main()
