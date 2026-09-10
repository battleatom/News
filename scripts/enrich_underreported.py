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
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by", "after", "new", "says", "said", "that", "this", "are", "was", "were", "has", "have", "had", "into", "over", "its", "their", "will", "amid", "more", "than"}
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
        req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 Underreported/2.0"})
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
            age_bonus = min(8, age_days / 30)
        score = overlap * 10 + age_bonus
        candidates.append((score, dt or datetime.min.replace(tzinfo=timezone.utc), t, link, desc, source, pub))

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected = []
    seen_sources = set()
    seen_titles = set()
    for row in candidates:
        normalized = re.sub(r"[^a-z0-9]", "", row[2].lower())
        if normalized in seen_titles:
            continue
        source_key = re.sub(r"[^a-z0-9]", "", row[5].lower()) or row[3]
        if source_key in seen_sources and len(selected) < 2:
            continue
        selected.append(row)
        seen_sources.add(source_key)
        seen_titles.add(normalized)
        if len(selected) >= MAX_RELATED:
            break
    return selected


def named_terms(text):
    raw = re.findall(r"\b[A-Z][A-Za-z0-9'’-]+(?:\s+[A-Z][A-Za-z0-9'’-]+){0,3}", text or "")
    bad = {"The", "This", "That", "After", "Before", "What", "When", "United States", "New York", "New Mexico"}
    return [x for x in raw if x not in bad][:4]


def specific_why(title, desc, category, related):
    text = f"{title} {desc}".lower()
    entities = named_terms(title)
    subject = ", ".join(entities[:2])
    if any(x in text for x in ("attack", "airstrike", "missile", "invasion", "troops", "war", "ceasefire", "strike")):
        return f"This matters because {subject + ' ' if subject else 'the development '}changes the military or diplomatic situation described in the report. The important question is whether it remains an isolated event or produces another response, escalation, or negotiation."
    if any(x in text for x in ("court", "ruling", "lawsuit", "supreme court", "executive order", "judge")):
        return f"This matters because {subject + ' ' if subject else 'the decision '}could change how the policy or legal dispute described here is applied. Its longer-term importance will depend on enforcement, appeals, or the precedent that follows."
    if any(x in text for x in ("congress", "senate", "house", "bill", "vote", "legislation")):
        return "This matters because the development moves the policy dispute described here into a new stage. The next vote, negotiation, amendment, or implementation decision can determine whether the change becomes consequential beyond today's headline."
    if any(x in text for x in ("tariff", "inflation", "recession", "layoffs", "bankruptcy", "price", "jobs")):
        return "This matters because the development can move costs, business decisions, employment, or consumer prices beyond the people directly named in the story. The lasting impact depends on how broadly the change spreads and how long it persists."
    if any(x in text for x in ("hack", "breach", "cyberattack", "outage", "data leak")):
        return "This matters because the affected system or organization may not be the only party exposed. The response, restoration timeline, and whether additional users or infrastructure are affected will determine the broader impact."
    if any(x in text for x in ("wildfire", "hurricane", "tornado", "earthquake", "drought", "flood", "contamination")):
        return "This matters because the immediate event can create secondary effects for people, infrastructure, public resources, and nearby communities. The scale of the response and whether conditions worsen are more important than the initial headline alone."
    if any(x in text for x in ("acquisition", "acquires", "studio closure", "shuts down", "canceled", "cancelled", "closure")):
        return "This matters because the organizational change can affect employees, customers, products, or services beyond the announcement itself. The important follow-through is what happens to the people and projects affected."
    if category == "military":
        return "This matters because the development changes or tests the security situation described in the reporting. Its importance will become clearer through the response from the other parties involved."
    return "This matters because the specific action described in the reporting could produce consequences beyond the immediate announcement. The key is what changes afterward, not simply that the announcement occurred."


def extract_useful_sentence(text):
    sentences = re.split(r"(?<=[.!?])\s+", text or "")
    for sentence in sentences:
        s = sentence.strip()
        if len(s) >= 55 and not re.fullmatch(r".*\b(?:AP News|Reuters|Fox News|CBS News|NBC News|CNN|The Washington Post)\b", s):
            return s
    return ""


def build_missing(title, desc, related):
    current = words(title)
    distinct = [row for row in related if len(current & words(row[2])) >= 2]
    if not related:
        return "The story has limited supporting coverage in the available search results. There is not enough evidence to identify a specific overlooked angle, so this section is not presenting one as fact."
    older = [r for r in related if r[1] < datetime.now(timezone.utc)]
    sources = len({r[5] for r in related if r[5]})
    if older:
        oldest = min(older, key=lambda r: r[1])
        age_days = max(1, (datetime.now(timezone.utc) - oldest[1]).days)
        return f"The immediate headline is receiving attention, but the longer-running thread is easier to miss. Supporting reporting goes back about {age_days} days, and the available coverage comes from {sources} source(s). That history suggests this is a continuing development rather than a standalone event."
    return f"The available reporting is concentrated in the current news cycle, with {sources} distinct source(s) represented in the supporting results. The limited spread of coverage is itself worth noting; there is not enough evidence to claim a more specific overlooked angle yet."


def build_background(related):
    older = [r for r in related if r[1] < datetime.now(timezone.utc)]
    if not older:
        return "No reliable older supporting report was identified. This story appears to be a newer development, so the section will expand as earlier reporting becomes available."
    older.sort(key=lambda r: r[1])
    pieces = []
    for row in older[:2]:
        date = row[1].strftime("%b %d, %Y") if row[1] != datetime.min.replace(tzinfo=timezone.utc) else "Earlier"
        detail = extract_useful_sentence(row[4])
        if detail:
            pieces.append(f"On {date}, {row[5] or 'another outlet'} reported: {detail}")
        else:
            pieces.append(f"On {date}, {row[5] or 'another outlet'} reported related developments under the headline '{row[2]}'.")
    return " ".join(pieces)


def what_next(desc, related):
    sentences = re.split(r"(?<=[.!?])\s+", desc or "")
    cues = ("will ", "plans to", "expected", "scheduled", "deadline", "next", "later", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "vote", "hearing", "trial", "meeting", "announce", "decision")
    matches = [s.strip() for s in sentences if any(c in s.lower() for c in cues) and len(s.strip()) >= 45]
    return matches[0] if matches else ""


def coverage_signal(related):
    """Return a bounded heuristic. Higher means less supporting coverage found."""
    source_count = len({clean(row[5]).lower() for row in related if clean(row[5])})
    result_count = len(related)
    score = max(50, min(96, 96 - source_count * 10 - max(0, result_count - source_count) * 4))
    if source_count == 0:
        label = "High underreporting signal"
    elif source_count <= 2:
        label = "Limited supporting coverage"
    else:
        label = "Growing supporting coverage"
    return score, source_count, label


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
        signal_score, supporting_sources, signal_label = coverage_signal(related)

        fields = {
            "whatHappened": desc if len(desc) >= 40 else f"The available report identifies this development: {title}.",
            "whyMatters": specific_why(title, desc, category, related),
            "whatIsMissing": build_missing(title, desc, related),
            "background": build_background(related),
            "whatNext": what_next(desc, related),
            "coverage": signal_label,
            "underreportedScore": str(signal_score),
            "supportingSourceCount": str(supporting_sources),
            "signalMethod": "Heuristic based on distinct supporting sources found in the related-news search; higher means less supporting coverage was found.",
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
    print(f"Underreported refinement complete: {enriched} stories enriched with context and a transparent coverage heuristic.")


if __name__ == "__main__":
    main()
