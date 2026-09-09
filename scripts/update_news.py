import hashlib
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

OUT = "News"
SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "nm", "local", "region", "nfl", "technology", "gaming", "military"]
MAX_AGE_HOURS = 48

QUERIES = {
    "nfl": [
        "NFL news",
        "NFL injuries trades free agency",
        "NFL scores results",
    ],
    "world": "world news OR international news",
    "us": "United States news OR US politics",
    "presidential": "Trump president White House",
    "federal": "US Congress OR federal government OR Supreme Court",
    "nm": "New Mexico government OR New Mexico news",
    "local": [
        "Farmington New Mexico news",
        "San Juan County New Mexico news",
        "Aztec New Mexico news",
        "Bloomfield New Mexico news",
        "Kirtland New Mexico news",
        "Shiprock New Mexico news",
        "Four Corners New Mexico news",
        "Farmington NM crime OR government OR education OR business",
    ],
    "region": {
        "southwest": [
            "Arizona news",
            "New Mexico news",
            "Colorado news",
            "Utah news",
            "Nevada news",
        ],
        "west": [
            "California news",
            "Nevada news",
            "Oregon news",
            "Washington state news",
        ],
        "mountain": [
            "Colorado news",
            "Utah news",
            "Idaho news",
            "Montana news",
            "Wyoming news",
        ],
        "midwest": [
            "Illinois news",
            "Michigan news",
            "Ohio news",
            "Wisconsin news",
            "Minnesota news",
            "Iowa news",
            "Missouri news",
            "Indiana news",
        ],
        "south": [
            "Texas news",
            "Oklahoma news",
            "Arkansas news",
            "Louisiana news",
            "Tennessee news",
            "Kentucky news",
            "Virginia news",
            "West Virginia news",
        ],
        "northeast": [
            "New York news",
            "Pennsylvania news",
            "New Jersey news",
            "Connecticut news",
            "Massachusetts news",
            "New England news",
            "Maine news",
            "New Hampshire news",
            "Vermont news",
            "Rhode Island news",
        ],
        "pacific-northwest": [
            "Washington state news",
            "Oregon news",
            "Idaho news",
            "Alaska news",
        ],
        "southeast": [
            "Florida news",
            "Georgia news",
            "Alabama news",
            "South Carolina news",
            "North Carolina news",
            "Mississippi news",
            "Tennessee news",
        ],
    },
    "nfl": ["NFL news", "NFL injuries trades free agency", "NFL scores results"],
    "technology": "technology AI cybersecurity science",
    "gaming": "Sony PlayStation OR Microsoft Xbox OR Nintendo OR Nvidia gaming OR PC gaming OR gaming hardware",
    "military": "military news OR Pentagon news OR defense news OR war news OR armed forces OR troops OR military conflict",
}

LOCAL_QUERIES = [
    "Farmington New Mexico news",
    "San Juan County New Mexico news",
    "Aztec New Mexico news",
    "Bloomfield New Mexico news",
    "Kirtland New Mexico news",
    "Shiprock New Mexico news",
    "Four Corners New Mexico news",
    "Farmington NM crime OR government OR education OR business",
]

MAINSTREAM_TOP_QUERIES = [
    ("Reuters", "site:reuters.com world US politics breaking news"),
    ("Associated Press", "site:apnews.com breaking news world US politics"),
    ("BBC", "site:bbc.com/news OR site:bbc.co.uk/news breaking world US"),
    ("CNN", "site:cnn.com breaking news world US politics"),
    ("Fox News", "site:foxnews.com breaking news US world politics"),
    ("NBC News", "site:nbcnews.com breaking news US world politics"),
    ("ABC News", "site:abcnews.go.com breaking news US world politics"),
    ("CBS News", "site:cbsnews.com breaking news US world politics"),
    ("The New York Times", "site:nytimes.com breaking news US world international"),
    ("The Washington Post", "site:washingtonpost.com breaking news US world politics"),
    ("NPR", "site:npr.org breaking news US world international"),
    ("USA Today", "site:usatoday.com breaking news US world"),
]

CATEGORY_WEIGHT = {"world": 18, "us": 22, "presidential": 24, "federal": 22, "military": 20, "nfl": 18, "technology": 12, "gaming": 16, "nm": 8, "local": 6}
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
    "acquisition": 12, "acquires": 12, "acquired": 12, "studio closure": 14, "shuts down": 14,
    "canceled": 10, "cancelled": 10, "delay": 8, "delayed": 8, "price increase": 10, "price hike": 10,
    "console": 5, "gpu": 8, "nvidia": 8, "playstation": 7, "xbox": 7, "nintendo": 7, "rtx": 7,
}
ROUTINE_TERMS = {"opinion": -10, "review": -8, "podcast": -8, "how to": -8, "watch": -5, "photos": -5, "best": -5, "guide": -5, "sale": -8, "deal": -8}


def feed_url(query):
    q = urllib.parse.quote(f"{query} when:2d")
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
    req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 NewsBrief/1.4"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read())


def parse_items(root, category, source_override=None):
    result = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    for item in root.findall(".//item"):
        title = clean(item.findtext("title")); link = item.findtext("link") or ""
        desc = clean(item.findtext("description")); pub = item.findtext("pubDate") or ""
        published = parse_date(pub); source_el = item.find("source")
        source = source_override or clean(source_el.text if source_el is not None else "")
        if not title or not link or not published or published < cutoff or published > now + timedelta(minutes=10):
            continue
        result.append({"title": title, "link": link, "description": desc, "pubDate": pub,
                       "published": published, "source": source, "category": category})
    return result


def key(item):
    title = item["title"]
    source = (item.get("source") or "").strip()
    if source:
        title = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", title, flags=re.IGNORECASE)
    domains = {"apnews.com", "reuters.com", "cnn.com", "foxnews.com", "nbcnews.com", "abcnews.go.com", "cbsnews.com", "npr.org", "usatoday.com", "bbc.com", "bbc.co.uk", "nytimes.com", "washingtonpost.com"}
    title = re.sub(r"\s+(?:[-–—|:]\s*)?(?:" + "|".join(re.escape(d) for d in domains) + r")\s*$", "", title, flags=re.IGNORECASE)
    words = re.findall(r"[a-z0-9]+", title.lower())
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by", "after", "new", "says"}
    return " ".join(w for w in words if w not in stop)[:180]


def source_key(source):
    s = re.sub(r"[^a-z0-9]+", "", (source or "").lower())
    aliases = {"delawareonline": "delawareonline", "delawareonlinecom": "delawareonline", "usatoday": "usatoday", "apnews": "associatedpress", "associatedpress": "associatedpress"}
    return aliases.get(s, s)


def impact_score(item, newest_time):
    text = f"{item['title']} {item['description']}".lower()
    score = CATEGORY_WEIGHT.get(item["category"], 0)
    for term, weight in HIGH_IMPACT_TERMS.items():
        if term in text:
            score += weight
    for term, weight in ROUTINE_TERMS.items():
        if term in text:
            score += weight
    age_hours = max(0.0, (newest_time - item["published"]).total_seconds() / 3600)
    score += max(0.0, 12.0 - age_hours * 0.35)
    if re.search(r"\b(update|announces|announced|orders|signs|votes|voted|dies|killed|launches|strikes|rules|approves)\b", text):
        score += 4
    return score


SUBJECT_ALIASES = {
    "iran": ("iran", "iranian", "tehran"),
    "israel": ("israel", "israeli", "gaza", "idf"),
    "russia": ("russia", "russian", "moscow", "putin"),
    "ukraine": ("ukraine", "ukrainian", "kyiv", "zelensky"),
    "china": ("china", "chinese", "beijing", "xi jinping"),
    "north korea": ("north korea", "north korean", "pyongyang", "kim jong un"),
    "donald trump": ("donald trump", "trump", "president trump"),
    "congress": ("congress", "senate", "house republicans", "house democrats"),
    "supreme court": ("supreme court", "scotus"),
    "fed": ("federal reserve", "fed", "jerome powell"),
    "nato": ("nato",),
    "gulf": ("strait of hormuz", "persian gulf", "gulf states"),
    "israel-palestine": ("palestinian", "palestine", "west bank"),
    "elon musk": ("elon musk", "musk", "spacex", "tesla"),
    "meta": ("meta", "facebook", "instagram", "zuckerberg"),
    "openai": ("openai", "chatgpt"),
    "google": ("google", "alphabet"),
    "apple": ("apple", "iphone"),
    "microsoft": ("microsoft", "windows", "xbox"),
    "nvidia": ("nvidia", "geforce", "rtx"),
    "amazon": ("amazon", "aws"),
}

def subject_keys(item):
    """Return major named subjects represented in a headline/description."""
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    return [subject for subject, aliases in SUBJECT_ALIASES.items()
            if any(re.search(rf"\\b{re.escape(alias)}\\b", text) for alias in aliases)]


def topic_key(item):
    """Return a broad topic bucket so one subject/event type cannot crowd out others."""
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    topic_terms = [
        ("military-conflict", ("war", "airstrike", "missile", "troops", "invasion", "ceasefire", "military conflict")),
        ("disaster-weather", ("earthquake", "hurricane", "tornado", "wildfire", "flood", "drought")),
        ("crime-public-safety", ("shooting", "killed", "murder", "police", "arrested", "missing")),
        ("economy-markets", ("inflation", "recession", "stocks", "market", "tariff", "oil prices", "unemployment")),
        ("government-politics", ("congress", "senate", "supreme court", "executive order", "election", "white house")),
        ("technology", ("ai", "artificial intelligence", "cyberattack", "hack", "software", "chip", "technology")),
        ("business", ("company", "acquisition", "layoffs", "bankruptcy", "earnings", "ceo")),
        ("science-space", ("nasa", "space", "rocket", "scientists", "study", "research")),
        ("sports", ("nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball")),
    ]
    for topic, terms in topic_terms:
        if any(term in text for term in terms):
            return topic
    return "general"

def select_top_stories(unique):
    """Build a diverse front page instead of letting one event dominate Top Stories."""
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)
    coverage = {}
    for item in unique:
        k = key(item)
        coverage.setdefault(k, set()).add(item["source"] or "Unknown")

    ranked = []
    for item in unique:
        k = key(item)
        outlet_count = len(coverage.get(k, set()))
        score = impact_score(item, newest_time) + min(30, outlet_count * 7)
        if outlet_count >= 4:
            score += 8
        ranked.append((score, item["published"], outlet_count, item))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)

    selected, seen_keys, source_counts = [], set(), {}
    subject_counts, topic_counts = {}, {}
    SUBJECT_CAP = 3
    TOPIC_CAP = 5
    MAX_PER_SOURCE = 2

    def add(item, relaxed=False):
        k = key(item)
        source = source_key(item["source"] or "Unknown")
        subjects = subject_keys(item)
        topic = topic_key(item)
        if not k or k in seen_keys or source_counts.get(source, 0) >= MAX_PER_SOURCE:
            return False
        if not relaxed:
            if subjects and max(subject_counts.get(s, 0) for s in subjects) >= SUBJECT_CAP:
                return False
            if topic_counts.get(topic, 0) >= TOPIC_CAP:
                return False
        selected.append(item)
        seen_keys.add(k)
        source_counts[source] = source_counts.get(source, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        for subject in subjects:
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
        return True

    # Pass 1 protects subject/topic variety while keeping the strongest stories.
    for _, _, _, item in ranked:
        add(item)
        if len(selected) == 30:
            break

    # Pass 2 fills remaining slots if today's news is unusually concentrated.
    # Duplicate and publisher protections remain active.
    if len(selected) < 30:
        for _, _, _, item in ranked:
            add(item, relaxed=True)
            if len(selected) == 30:
                break

    print("TOP diversity subjects: " + ", ".join(f"{k}={v}" for k, v in sorted(subject_counts.items(), key=lambda x: (-x[1], x[0]))[:12]))
    print("TOP diversity topics: " + ", ".join(f"{k}={v}" for k, v in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))))
    return selected


def select_underreported(unique):
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)
    coverage = {}
    for item in unique:
        k = key(item)
        coverage.setdefault(k, set()).add(source_key(item["source"] or "Unknown"))
    candidates = []
    for item in unique:
        k = key(item); sources = len(coverage.get(k, set())); impact = impact_score(item, newest_time)
        if impact < 22:
            continue
        under_score = impact + max(0, 18 - sources * 6)
        if sources <= 1:
            under_score += 8
        candidates.append((under_score, item["published"], item))
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected, seen_keys, source_counts = [], set(), {}
    for _, _, item in candidates:
        k = key(item); source = source_key(item["source"] or "Unknown")
        if k in seen_keys or source_counts.get(source, 0) >= 2:
            continue
        selected.append(item); seen_keys.add(k); source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) == 30:
            break
    return selected


def select_category_stories(items, limit=30):
    """Select up to 30 distinct stories, with Local queries treated as the geographic scope."""
    if items and items[0].get("category") == "local":
        local_terms = (
            "farmington", "san juan county", "san juan regional", "aztec", "bloomfield",
            "kirtland", "shiprock", "navajo nation", "four corners", "san juan basin",
            "farmington daily times", "daily times", "navajo times", "krtm", "ksje",
        )
        outside_terms = (
            "california", "texas", "florida", "new york", "chicago", "atlanta",
            "phoenix", "denver", "las vegas", "albuquerque", "santa fe",
        )
        local_items = []
        for item in items:
            title = (item.get("title") or "").lower()
            source = (item.get("source") or "").lower()
            desc = (item.get("description") or "").lower()
            local_signal = any(term in title or term in source for term in local_terms)
            outside_signal = any(term in title for term in outside_terms)
            if local_signal and not outside_signal:
                local_items.append(item)
        # Prefer strongly identified local stories, but do not let publisher
        # diversity or a brittle second geography filter reduce the category.
        items = local_items

    ranked = sorted(items, key=lambda x: x["published"], reverse=True)
    selected, seen_keys, seen_sources = [], set(), set()

    # Pass 1: maximize publisher diversity.
    for item in ranked:
        k = key(item); source = source_key(item["source"] or "Unknown")
        if not k or k in seen_keys or source in seen_sources:
            continue
        selected.append(item); seen_keys.add(k); seen_sources.add(source)
        if len(selected) == limit:
            return selected

    # Pass 2: fill every remaining slot with distinct stories.
    for item in ranked:
        k = key(item)
        if not k or k in seen_keys:
            continue
        selected.append(item); seen_keys.add(k)
        if len(selected) == limit:
            break
    return selected

def why_matters(item):
    text = f"{item['title']} {item['description']}".lower()
    if any(t in text for t in ("war", "invasion", "airstrike", "missile", "ceasefire", "military", "troops")):
        reason = "could have broader security or geopolitical consequences"
    elif any(t in text for t in ("congress", "supreme court", "executive order", "federal", "president", "white house", "ruling", "lawsuit")):
        reason = "could affect government policy, rights, or public institutions"
    elif any(t in text for t in ("tariff", "inflation", "recession", "bankruptcy", "layoffs", "economy")):
        reason = "could have wider economic consequences"
    elif any(t in text for t in ("hack", "breach", "cyberattack", "outage", "technology")):
        reason = "could affect security, infrastructure, or technology users"
    elif item["category"] == "gaming":
        reason = "could affect gamers, gaming hardware, major platforms, or the wider games industry"
    elif any(t in text for t in ("wildfire", "hurricane", "tornado", "earthquake", "drought", "water crisis", "contamination")):
        reason = "could affect public safety or essential resources"
    elif item["category"] in ("nm", "local"):
        reason = "could have consequences beyond the immediate local story"
    else:
        reason = "has potential consequences beyond the immediate headline"
    return "Why it matters: " + reason + "."


def xml_escape(value):
    return html.escape(value or "", quote=False)


def build(items):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>', '<title>Underreported News Brief</title>', '<link>https://battleatom.github.io/News/</link>', '<description>High-impact stories outside the usual news cycle</description>', f'<lastBuildDate>{now}</lastBuildDate>']
    for item in items:
        guid = hashlib.sha1((item["link"] + "|" + item["category"]).encode("utf-8")).hexdigest()
        out += ["<item>", f'<title>{xml_escape(item["title"])}</title>', f'<link>{xml_escape(item["link"])}</link>', f'<description>{xml_escape(item.get("description", ""))}</description>', f'<pubDate>{xml_escape(item["pubDate"])}</pubDate>', f'<source>{xml_escape(item["source"])}</source>', f'<category>{item["category"]}</category>', f'<region>{xml_escape(item.get("region", ""))}</region>', f'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>', f'<guid isPermaLink="false">{guid}</guid>', "</item>"]
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


def main():
    all_items = []
    for category, query in QUERIES.items():
        try:
            if category == "local":
                items = []
                for local_query in LOCAL_QUERIES:
                    try:
                        batch = parse_items(fetch(local_query), category)
                        print(f"local/{local_query}: {len(batch)} fresh stories")
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Local feed failed for {local_query}: {exc}")
            elif category == "region":
                items = []
                for region_name, region_queries in query.items():
                    region_count = 0
                    for region_query in region_queries:
                        try:
                            batch = parse_items(fetch(region_query), category)
                            for item in batch:
                                item["region"] = region_name
                            region_count += len(batch)
                            items.extend(batch)
                        except Exception as exc:
                            print(f"Region feed failed for {region_name}/{region_query}: {exc}")
                    print(f"region/{region_name}: {region_count} fresh stories")
            else:
                items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")
            all_items.extend(items)
        except Exception as exc:
            print(f"Feed failed for {category}: {exc}")

    mainstream_items = []
    for source_name, query in MAINSTREAM_TOP_QUERIES:
        try:
            items = parse_items(fetch(query), "us", source_override=source_name)
            print(f"top/{source_name}: {len(items)} fresh stories")
            mainstream_items.extend(items)
        except Exception as exc:
            print(f"Top feed failed for {source_name}: {exc}")

    seen, unique = set(), []
    for item in sorted(all_items, key=lambda x: x["published"], reverse=True):
        k = key(item)
        if not k or k in seen:
            continue
        seen.add(k); unique.append(item)

    top_seen, top_unique = set(), []
    for item in sorted(mainstream_items, key=lambda x: x["published"], reverse=True):
        k = key(item)
        if not k or k in top_seen:
            continue
        top_seen.add(k); top_unique.append(item)

    selected_by_category = {}
    for category in SECTIONS[2:]:
        category_items = [x for x in unique if x["category"] == category]
        if category == "region":
            selected_by_category[category] = []
            for region_name in ("southwest", "west", "mountain", "midwest", "south", "northeast", "pacific-northwest", "southeast"):
                region_items = [x for x in category_items if x.get("region") == region_name]
                selected_by_category[category].extend(select_category_stories(region_items, limit=30))
        else:
            selected_by_category[category] = select_category_stories(category_items)
    top = select_top_stories(top_unique)
    underreported = select_underreported(unique)

    top_items = []
    for item in top:
        copy = dict(item); copy["category"] = "top"; top_items.append(copy)

    under_items = []
    for item in underreported:
        copy = dict(item); copy["category"] = "underreported"; copy["whyMatters"] = why_matters(item); under_items.append(copy)

    ordered = top_items + under_items
    for category in SECTIONS[2:]:
        chosen = selected_by_category[category]
        print(f"FINAL {category}: {len(chosen)} stories")
        ordered.extend(chosen)

    if not ordered:
        raise RuntimeError("No fresh stories were retrieved; refusing to overwrite News with an empty feed.")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(ordered))
    print(f"Wrote {len(ordered)} fresh stories to {OUT}")
    print(f"Top Stories: {len(top_items)} mainstream | Underreported: {len(under_items)} low-coverage/high-impact")


if __name__ == "__main__":
    main()
