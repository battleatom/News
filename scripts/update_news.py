import hashlib
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

OUT = "News"
SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "nm", "local", "technology", "military"]
MAX_AGE_HOURS = 72

QUERIES = {
    "world": "world news OR international news",
    "us": "United States news OR US politics",
    "presidential": "Trump president White House",
    "federal": "US Congress OR federal government OR Supreme Court",
    "nm": "New Mexico government OR New Mexico news",
    "local": "Farmington New Mexico OR Four Corners New Mexico",
    "technology": "technology AI cybersecurity science",
    "military": "military news OR Pentagon news OR defense news OR war news OR armed forces OR troops OR military conflict",
}

CATEGORY_WEIGHT = {"world": 18, "us": 22, "presidential": 24, "federal": 22, "military": 20, "technology": 12, "nm": 8, "local": 4}
HIGH_IMPACT_TERMS = {
    "war": 18, "invasion": 18, "attack": 16, "airstrike": 16, "missile": 16, "ceasefire": 15,
    "conflict": 12, "crisis": 12, "emergency": 12, "sanctions": 10, "tariff": 10, "tariffs": 10,
    "shutdown": 12, "impeach": 14, "impeachment": 14, "supreme court": 14, "executive order": 12,
    "president": 8, "trump": 8, "white house": 8, "congress": 8, "election": 12, "elections": 12,
    "iran": 10, "israel": 8, "ukraine": 10, "russia": 8, "china": 8, "north korea": 10, "nato": 8,
    "earthquake": 15, "hurricane": 15, "tornado": 14, "wildfire": 14, "mass shooting": 18,
    "shooting": 12, "killed": 10, "dead": 8, "breaking": 10, "breaking news": 12,
    "outage": 10, "breach": 12, "hack": 12, "cyberattack": 15, "lawsuit": 8, "ruling": 10,
    "ban": 9, "recall": 10, "layoffs": 8, "bankruptcy": 12, "inflation": 8, "recession": 12,
    "water crisis": 16, "drought": 12, "contamination": 12,
}
ROUTINE_TERMS = {"opinion": -10, "review": -8, "podcast": -8, "how to": -8, "watch": -5, "photos": -5, "best": -5, "guide": -5}


def feed_url(query):
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
    req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 NewsBrief/1.3"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read())


def parse_items(root, category):
    result = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    for item in root.findall(".//item"):
        title = clean(item.findtext("title")); link = item.findtext("link") or ""
        desc = clean(item.findtext("description")); pub = item.findtext("pubDate") or ""
        published = parse_date(pub); source_el = item.find("source")
        source = clean(source_el.text if source_el is not None else "")
        if not title or not link or not published or published < cutoff or published > now + timedelta(minutes=10):
            continue
        result.append({"title": title, "link": link, "description": desc, "pubDate": pub,
                       "published": published, "source": source, "category": category})
    return result


def key(item):
    words = re.findall(r"[a-z0-9]+", item["title"].lower())
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by", "after", "new", "says"}
    return " ".join(w for w in words if w not in stop)[:180]


def impact_score(item, newest_time):
    text = f"{item['title']} {item['description']}".lower()
    score = CATEGORY_WEIGHT.get(item["category"], 0)
    for term, weight in HIGH_IMPACT_TERMS.items():
        if term in text: score += weight
    for term, weight in ROUTINE_TERMS.items():
        if term in text: score += weight
    age_hours = max(0.0, (newest_time - item["published"]).total_seconds() / 3600)
    score += max(0.0, 12.0 - age_hours * 0.35)
    if re.search(r"\b(update|announces|announced|orders|signs|votes|voted|dies|killed|launches|strikes|rules|approves)\b", text): score += 4
    return score


def select_top_stories(unique):
    if not unique: return []
    newest_time = max(x["published"] for x in unique)
    ranked = sorted(unique, key=lambda x: (impact_score(x, newest_time), x["published"]), reverse=True)
    selected, category_counts, source_counts = [], {}, {}
    for item in ranked:
        category = item["category"]; source = item["source"] or "Unknown"
        if category_counts.get(category, 0) >= 4 or source_counts.get(source, 0) >= 2: continue
        selected.append(item); category_counts[category] = category_counts.get(category, 0) + 1; source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) == 10: break
    return selected


def select_underreported(unique):
    if not unique: return []
    newest_time = max(x["published"] for x in unique)
    coverage = {}
    for item in unique:
        k = key(item)
        coverage.setdefault(k, set()).add((item["source"] or "Unknown").lower())
    candidates = []
    for item in unique:
        k = key(item); sources = len(coverage.get(k, set())); impact = impact_score(item, newest_time)
        if impact < 22: continue
        # High impact with few independent source appearances gets the strongest underreported score.
        under_score = impact + max(0, 18 - sources * 6)
        if sources <= 1: under_score += 8
        candidates.append((under_score, item["published"], item))
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected, seen_keys, source_counts = [], set(), {}
    for score, _, item in candidates:
        k = key(item); source = item["source"] or "Unknown"
        if k in seen_keys or source_counts.get(source, 0) >= 2: continue
        selected.append(item); seen_keys.add(k); source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) == 12: break
    return selected


def why_matters(item):
    text = f"{item['title']} {item['description']}".lower()
    reasons = []
    if any(t in text for t in ("war", "invasion", "airstrike", "missile", "ceasefire", "military", "troops")): reasons.append("could have broader security or geopolitical consequences")
    elif any(t in text for t in ("congress", "supreme court", "executive order", "federal", "president", "white house", "ruling", "lawsuit")): reasons.append("could affect government policy, rights, or public institutions")
    elif any(t in text for t in ("tariff", "inflation", "recession", "bankruptcy", "layoffs", "economy")): reasons.append("could have wider economic consequences")
    elif any(t in text for t in ("hack", "breach", "cyberattack", "outage", "technology")): reasons.append("could affect security, infrastructure, or technology users")
    elif any(t in text for t in ("wildfire", "hurricane", "tornado", "earthquake", "drought", "water crisis", "contamination")): reasons.append("could affect public safety or essential resources")
    elif item["category"] in ("nm", "local"): reasons.append("could have consequences beyond the immediate local story")
    else: reasons.append("has potential consequences beyond the immediate headline")
    return "Why it matters: " + reasons[0] + "."


def xml_escape(value): return html.escape(value or "", quote=False)


def build(items):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>', '<title>Underreported News Brief</title>',
           '<link>https://battleatom.github.io/News/</link>', '<description>High-impact stories outside the usual news cycle</description>', f'<lastBuildDate>{now}</lastBuildDate>']
    for item in items:
        guid = hashlib.sha1((item["link"] + "|" + item["category"]).encode("utf-8")).hexdigest()
        out += ["<item>", f'<title>{xml_escape(item["title"])}</title>', f'<link>{xml_escape(item["link"])}</link>',
                f'<description>{xml_escape(item.get("description", ""))}</description>', f'<pubDate>{xml_escape(item["pubDate"])}</pubDate>',
                f'<source>{xml_escape(item["source"])}</source>', f'<category>{item["category"]}</category>',
                f'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>', f'<guid isPermaLink="false">{guid}</guid>', "</item>"]
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


def main():
    all_items = []
    for category, query in QUERIES.items():
        try:
            items = parse_items(fetch(query), category); print(f"{category}: {len(items)} fresh stories"); all_items.extend(items)
        except Exception as exc: print(f"Feed failed for {category}: {exc}")

    seen, unique = set(), []
    for item in sorted(all_items, key=lambda x: x["published"], reverse=True):
        k = key(item)
        if not k or k in seen: continue
        seen.add(k); unique.append(item)

    selected_by_category = {category: [x for x in unique if x["category"] == category][:10] for category in SECTIONS[2:]}
    top = select_top_stories(unique); underreported = select_underreported(unique)

    top_items = []
    for item in top:
        copy = dict(item); copy["category"] = "top"; copy["whyMatters"] = why_matters(item); top_items.append(copy)
    under_items = []
    for item in underreported:
        copy = dict(item); copy["category"] = "underreported"; copy["whyMatters"] = why_matters(item); under_items.append(copy)

    ordered = top_items + under_items
    for category in SECTIONS[2:]:
        for item in selected_by_category[category]:
            if item not in ordered: ordered.append(item)
    if not ordered: raise RuntimeError("No fresh stories were retrieved; refusing to overwrite News with an empty feed.")

    with open(OUT, "w", encoding="utf-8") as f: f.write(build(ordered))
    print(f"Wrote {len(ordered)} fresh stories to {OUT}")
    print(f"Top Stories: {len(top_items)} | Underreported: {len(under_items)}")


if __name__ == "__main__": main()
