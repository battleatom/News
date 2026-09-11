import hashlib
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

OUT = "News"
SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "legislation", "nm", "local", "region", "nfl", "technology", "gaming", "military"]
MAX_AGE_HOURS = 48

US_STATE_NAMES = {
    'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming'
}

def region_query_state(query):
    candidate=re.sub(r'\s+news$', '', str(query), flags=re.I).strip()
    if candidate.lower()=='washington state': candidate='Washington'
    return candidate if candidate in US_STATE_NAMES else ''


QUERIES = {
    "nfl": [
        "NFL news",
        "NFL injuries trades free agency",
        "NFL scores results",
    ],
    "world": "world news OR international news",
    "us": "United States news OR US politics",
    "presidential": [
        "Trump president White House",
        "President Trump administration White House policy",
        "Trump executive order presidential action White House",
        "Trump cabinet administration president",
    ],
    "federal": [
        "US Congress Senate House legislation committee federal government",
        "US Supreme Court federal appeals court federal judge",
        "DOJ FBI DHS federal agency government policy",
        "EPA FTC SEC FCC IRS federal regulation rule",
        "US Treasury State Department federal government agency",
        "federal budget spending government shutdown Congress",
    ],
    "legislation": [
        "US Congress bill legislation passed signed law House Senate",
        "executive order presidential action federal regulation final rule",
        "site:congress.gov bill law House Senate",
        "site:federalregister.gov rule regulation final rule",
        "site:whitehouse.gov presidential actions executive order",
        "New Mexico Legislature bill passed signed law governor",
        "site:nmlegis.gov legislation bill",
        "New Mexico executive order regulation governor",
        "Farmington NM ordinance city council law",
        "San Juan County NM ordinance commission regulation",
    ],
    "nm": "New Mexico government OR New Mexico news",
    "local": [
        "Farmington New Mexico news",
        "San Juan County New Mexico news",
        "Aztec New Mexico news",
        "Bloomfield New Mexico news",
        "Kirtland New Mexico news",
        "Shiprock New Mexico news",
        "Four Corners news",
        "Durango Colorado news",
        "La Plata County Colorado news",
        "Cortez Colorado news",
        "Montezuma County Colorado news",
        "Gallup New Mexico news",
        "Window Rock Arizona news",
        "Navajo Nation news",
        "Blanding Utah news",
        "San Juan County Utah news",
        "Farmington NM crime government education business",
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
    "technology": [
        "AI technology news",
        "cybersecurity data breach technology",
        "Microsoft Google Apple Nvidia technology",
        "semiconductor software cloud computing news",
    ],
    "gaming": [
        "PlayStation Xbox Nintendo gaming news",
        "PC gaming Nvidia AMD gaming hardware",
        "video game industry releases studios gaming",
    ],
    "military": [
        "Pentagon US military defense news",
        "US armed forces troops military news",
        "defense industry military conflict news",
    ],
}

LOCAL_QUERIES = [
    "Farmington New Mexico news",
    "San Juan County New Mexico news",
    "Aztec New Mexico news",
    "Bloomfield New Mexico news",
    "Kirtland New Mexico news",
    "Shiprock New Mexico news",
    "Four Corners news",
    "Durango Colorado news",
    "La Plata County Colorado news",
    "Cortez Colorado news",
    "Montezuma County Colorado news",
    "Gallup New Mexico news",
    "Window Rock Arizona news",
    "Navajo Nation news",
    "Blanding Utah news",
    "San Juan County Utah news",
    "Farmington NM crime government education business",
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

TRUSTED_CATEGORY_FALLBACKS = {
    "presidential": [
        ("Reuters", "site:reuters.com Trump White House president administration"),
        ("Associated Press", "site:apnews.com Trump White House president administration"),
        ("Politico", "site:politico.com Trump White House president administration"),
        ("CNN", "site:cnn.com Trump White House president administration"),
        ("CBS News", "site:cbsnews.com Trump White House president administration"),
    ],
    "federal": [
        ("Reuters", "site:reuters.com Congress Supreme Court DOJ FBI federal agency government"),
        ("Associated Press", "site:apnews.com Congress Supreme Court DOJ FBI federal government"),
        ("Politico", "site:politico.com Congress Supreme Court federal agency government"),
        ("The Hill", "site:thehill.com Congress Supreme Court federal agency government"),
        ("NPR", "site:npr.org Congress Supreme Court federal government agency"),
    ],
    "local": [
        ("Tri-City Record", "site:tricityrecordnm.com (Farmington OR \"San Juan County\" OR Aztec OR Bloomfield OR Kirtland OR Shiprock OR \"Four Corners\")"),
        ("KSJE", "site:ksje.com (Farmington OR \"San Juan County\" OR Aztec OR Bloomfield OR Kirtland OR Shiprock OR \"Four Corners\")"),
        ("Navajo Times", "site:navajotimes.com (Shiprock OR Farmington OR \"San Juan County\" OR \"Four Corners\")"),
        ("Durango Herald", "site:durangoherald.com (Farmington OR Shiprock OR Aztec OR \"San Juan County\" OR \"Four Corners\")"),
        ("The Journal", "site:the-journal.com (Farmington OR Shiprock OR Cortez OR \"Four Corners\")"),
    ],
    "nfl": [
        ("ESPN", "site:espn.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),
        ("NFL.com", "site:nfl.com/news (NFL OR football OR injury OR trade OR roster OR game)"),
        ("CBS Sports", "site:cbssports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),
        ("NBC Sports", "site:nbcsports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),
        ("Fox Sports", "site:foxsports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),
        ("Yahoo Sports", "site:sports.yahoo.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),
    ],
    "technology": [
        ("The Verge", "site:theverge.com (AI OR technology OR cybersecurity OR Microsoft OR Apple OR Google OR Nvidia)"),
        ("Ars Technica", "site:arstechnica.com (AI OR technology OR security OR software OR chips OR computing)"),
        ("TechCrunch", "site:techcrunch.com (AI OR technology OR cybersecurity OR software OR startups)"),
        ("Wired", "site:wired.com (AI OR technology OR cybersecurity OR computing)"),
        ("Tom's Hardware", "site:tomshardware.com (Nvidia OR AMD OR Intel OR GPU OR CPU OR hardware)"),
    ],
    "gaming": [
        ("IGN", "site:ign.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo OR PC gaming)"),
        ("GameSpot", "site:gamespot.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo)"),
        ("PC Gamer", "site:pcgamer.com (gaming OR PC gaming OR Nvidia OR AMD OR Steam)"),
        ("Nintendo Life", "site:nintendolife.com (Nintendo OR Switch OR gaming OR games)"),
        ("Polygon", "site:polygon.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo)"),
    ],
}

CATEGORY_WEIGHT = {"world": 18, "us": 22, "presidential": 24, "federal": 22, "legislation": 24, "military": 20, "nfl": 18, "technology": 12, "gaming": 16, "nm": 8, "local": 6}
CATEGORY_POOL_MINIMUMS = {'local': 20, 'nfl': 20, 'presidential': 20, 'federal': 25, 'technology': 25, 'gaming': 25}
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



TRUSTED_SOURCE_TOKENS = ('aap', 'abc australia', 'abc news', 'afp', 'al jazeera', 'albuquerque journal', 'ap', 'arizona republic', 'ars technica', 'associated press', 'australian broadcasting corporation', 'axios', 'azcentral', 'bbc', 'bloomberg', 'boston globe', 'breaking defense', 'cbc', 'cbs news', 'chicago tribune', 'cnbc', 'cnn', 'colorado public radio', 'corriere della sera', 'daily times', 'defense news', 'denver post', 'denver7', 'der spiegel', 'destructoid', 'deutsche presse agentur', 'deutsche welle', 'dpa', 'durango herald', 'durango telegraph', 'dw', 'el pais', 'engadget', 'eurogamer', 'euronews', 'farmington daily times', 'forbes', 'fox news', 'france 24', 'france24', 'game informer', 'gamespot', 'haaretz', 'ign', 'janes', 'jerusalem post', 'kfox', 'koaa', 'koat', 'kob 4', 'kob tv', 'kotaku', 'krdo', 'krqe', 'kvia', 'kyiv independent', 'las cruces sun news', 'le monde', 'los angeles times', 'military times', 'mit technology review', 'nature', 'nbc news', 'new mexico in depth', 'new york times', 'newsweek', 'nhk', 'nintendo life', 'nm political report', 'npr', 'pbs', 'pc gamer', 'pc magazine', 'pcmag', 'politico', 'politico europe', 'polygon', 'reuters', 'rfi', 'rock paper shotgun', 'santa fe new mexican', 'scientific american', 'sky news', 'south china morning post', 'space com', 'stars and stripes', 'swissinfo', 'techcrunch', 'the colorado sun', 'the gamer', 'the guardian', 'the hill', 'the hindu', 'the telegraph', 'the times', 'the verge', 'time', 'times of india', 'times of israel', 'tom s hardware', 'usa today', 'usatoday', 'wall street journal', 'war on the rocks', 'washington post', 'wired', 'wsj', 'yahoo finance', 'yahoo news')
TRUSTED_LOCAL_SOURCE_TOKENS = (
    "tri city record", "ksje", "navajo times", "durango herald", "the journal",
)
TRUSTED_SOURCE_TOKENS = tuple(sorted(set(TRUSTED_SOURCE_TOKENS) | set(TRUSTED_LOCAL_SOURCE_TOKENS)))

TRUSTED_SPORTS_SOURCE_TOKENS = (
    "espn", "nfl com", "cbs sports", "nbc sports", "fox sports",
    "yahoo sports", "sports illustrated", "pro football talk",
)
TRUSTED_SOURCE_TOKENS = tuple(sorted(set(TRUSTED_SOURCE_TOKENS) | set(TRUSTED_SPORTS_SOURCE_TOKENS)))

PUBLIC_INTEREST_SOURCE_TOKENS = (
    "propublica", "the marshall project", "kff health news", "kaiser health news",
    "inside climate news", "insideclimate news", "grist", "reveal", "center for public integrity",
    "source new mexico", "searchlight new mexico", "stateline", "states newsroom",
    "new mexico in depth", "capital and main", "the 19th", "route fifty", "congress gov", "congress.gov", "federal register", "federalregister.gov",
    "white house", "whitehouse.gov", "new mexico legislature", "nmlegis.gov",
    "governor of new mexico", "gao", "government accountability office",
)
TRUSTED_SOURCE_TOKENS = tuple(sorted(set(TRUSTED_SOURCE_TOKENS) | set(PUBLIC_INTEREST_SOURCE_TOKENS)))

UNDERREPORTED_DISCOVERY_QUERIES = [
    ("ProPublica", "site:propublica.org investigation government health environment labor justice"),
    ("The Marshall Project", "site:themarshallproject.org criminal justice prisons policing investigation"),
    ("KFF Health News", "site:kffhealthnews.org health policy hospitals Medicaid investigation"),
    ("Inside Climate News", "site:insideclimatenews.org climate water pollution environment investigation"),
    ("Grist", "site:grist.org climate environment water energy policy"),
    ("Reveal", "site:revealnews.org investigation labor housing justice government"),
    ("New Mexico In Depth", "site:nmindepth.com New Mexico investigation government education health"),
    ("Source New Mexico", "site:sourcenm.com New Mexico legislature environment health labor"),
    ("Searchlight New Mexico", "site:searchlightnm.org New Mexico investigation children health government"),
    ("Stateline", "site:stateline.org state policy legislation health housing labor"),
]

LEGISLATION_JOURNALISM_QUERIES = [
    ("Source New Mexico", "site:sourcenm.com (bill OR legislature OR law OR regulation OR executive order) New Mexico"),
    ("New Mexico In Depth", "site:nmindepth.com (bill OR legislature OR law OR regulation) New Mexico"),
    ("Searchlight New Mexico", "site:searchlightnm.org (bill OR law OR legislature OR regulation) New Mexico"),
    ("Tri-City Record", "site:tricityrecordnm.com (ordinance OR city council OR county commission OR law) Farmington"),
    ("Durango Herald", "site:durangoherald.com (ordinance OR city council OR county commission OR law) Durango"),
    ("The Journal", "site:the-journal.com (ordinance OR city council OR county commission OR law) Cortez"),
]

UNDERREPORTED_PAYWALL_SOURCE_TOKENS = (
    "new york times", "the new york times", "wall street journal", "wsj",
    "bloomberg", "washington post", "the washington post",
)
UNDERREPORTED_PUBLIC_INTEREST_TOKENS = (
    "propublica", "marshall project", "kff health news", "kaiser health news",
    "inside climate", "grist", "reveal", "public integrity", "source new mexico",
    "searchlight new mexico", "new mexico in depth", "stateline", "states newsroom",
    "npr", "pbs", "public radio",
)

FOREIGN_ONLY_TERMS = ('germany', 'german', 'berlin', 'france', 'french', 'paris', 'united kingdom', 'britain', 'british', 'london', 'italy', 'italian', 'rome', 'spain', 'spanish', 'madrid', 'europe', 'european union', 'eu', 'ukraine', 'ukrainian', 'russia', 'russian', 'moscow', 'china', 'chinese', 'beijing', 'japan', 'japanese', 'tokyo', 'south korea', 'korean', 'india', 'indian', 'africa', 'african', 'south africa', 'nigeria', 'kenya', 'ethiopia', 'ghana', 'egypt', 'cairo', 'israel', 'israeli', 'gaza', 'palestine', 'iran', 'iranian', 'tehran', 'iraq', 'iraqi', 'syria', 'syrian', 'lebanon', 'turkey', 'turkish', 'australia', 'australian', 'canada', 'canadian', 'mexico', 'mexican', 'brazil', 'brazilian', 'argentina', 'argentine', 'colombia', 'philippines', 'indonesia', 'taiwan', 'new zealand', 'pakistan', 'afghanistan', 'north korea', 'nato', 'united nations', 'west bank')
US_CONTEXT_TERMS = ('united states', 'u.s.', 'us ', 'america', 'american', 'washington dc', 'washington, d.c.', 'new mexico', 'farmington', 'san juan county', 'arizona', 'colorado', 'utah', 'nevada', 'texas', 'california', 'oregon', 'washington state', 'new york', 'florida', 'georgia', 'illinois', 'ohio', 'congress', 'senate', 'house of representatives', 'white house', 'pentagon', 'supreme court')

PRESIDENTIAL_DIRECT_TERMS = (
    "donald trump", "president trump", "trump", "white house",
    "u.s. president", "us president", "president of the united states",
    "oval office", "trump administration", "vice president vance",
    "jd vance", "j.d. vance", "karoline leavitt", "white house press secretary",
)
PRESIDENTIAL_ACTION_TERMS = (
    "executive order", "presidential action", "presidential memorandum",
    "presidential proclamation", "cabinet meeting", "administration official",
)

def is_us_presidential_story(title, description=""):
    title_text = f" {clean(title).lower()} "
    full_text = f" {clean(title).lower()} {clean(description).lower()} "
    if any(term in title_text for term in PRESIDENTIAL_DIRECT_TERMS):
        return True
    us_context = any(term in full_text for term in ("united states", "u.s.", "american", "white house"))
    return us_context and any(term in full_text for term in PRESIDENTIAL_ACTION_TERMS)


def source_is_trusted(source):
    s = re.sub(r"[^a-z0-9]+", " ", (source or "").lower()).strip()
    if not s:
        return False
    padded = f" {s} "
    return any(s == token or f" {token} " in padded for token in TRUSTED_SOURCE_TOKENS)

def should_route_to_world(title, description, category):
    if category == "world":
        return False
    text = f"{title} {description}".lower()
    if category in ("gaming", "technology"):
        domain_terms = (
            "gaming", "video game", "playstation", "xbox", "nintendo", "switch", "steam", "game studio",
            "technology", "software", "hardware", "artificial intelligence", " ai ", "chip", "semiconductor",
            "gpu", "cpu", "nvidia", "amd", "intel", "microsoft", "apple", "google", "android", "iphone",
            "cybersecurity", "data breach", "cloud computing",
        )
        geopolitical_terms = (
            "government", "president", "prime minister", "parliament", "election", "military", "war",
            "sanction", "tariff", "diplomat", "embassy", "protest", "attack", "invasion", "ceasefire",
            "foreign ministry", "defense ministry", "national security law",
        )
        padded = f" {text} "
        if any(term in padded for term in domain_terms) and not any(term in text for term in geopolitical_terms):
            return False
    foreign_hits = sum(1 for term in FOREIGN_ONLY_TERMS if term in text)
    us_hits = sum(1 for term in US_CONTEXT_TERMS if term in text)
    return foreign_hits >= 2 and us_hits == 0

def parse_date(value):
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


FETCH_CACHE = {}


def fetch(query):
    cache_key = str(query).strip()
    payload = FETCH_CACHE.get(cache_key)
    if payload is None:
        req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 NewsBrief/2.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = response.read()
        FETCH_CACHE[cache_key] = payload
    return ET.fromstring(payload)


def parse_items(root, category, source_override=None):
    result = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    for item in root.findall(".//item"):
        title = clean(item.findtext("title")); link = item.findtext("link") or ""
        desc = clean(item.findtext("description")); pub = item.findtext("pubDate") or ""
        published = parse_date(pub); source_el = item.find("source")
        source = source_override or clean(source_el.text if source_el is not None else "")
        if not source_is_trusted(source):
            continue
        if category == "presidential" and not is_us_presidential_story(title, desc):
            continue
        item_category = "world" if should_route_to_world(title, desc, category) else category
        if not title or not link or not published or published < cutoff or published > now + timedelta(minutes=10):
            continue
        result.append({"title": title, "link": link, "description": desc, "pubDate": pub,
                       "published": published, "source": source, "category": item_category})
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


SUBJECT_ALIASES = {'iran': ('iran', 'iranian', 'tehran'), 'israel': ('israel', 'israeli', 'gaza', 'idf'), 'russia': ('russia', 'russian', 'moscow', 'putin'), 'ukraine': ('ukraine', 'ukrainian', 'kyiv', 'zelensky'), 'china': ('china', 'chinese', 'beijing', 'xi jinping'), 'north korea': ('north korea', 'north korean', 'pyongyang', 'kim jong un'), 'donald trump': ('donald trump', 'trump', 'president trump'), 'congress': ('congress', 'senate', 'house republicans', 'house democrats'), 'supreme court': ('supreme court', 'scotus'), 'fed': ('federal reserve', 'fed', 'jerome powell'), 'nato': ('nato',), 'gulf': ('strait of hormuz', 'persian gulf', 'gulf states'), 'israel-palestine': ('palestinian', 'palestine', 'west bank'), 'elon musk': ('elon musk', 'musk', 'spacex', 'tesla'), 'meta': ('meta', 'facebook', 'instagram', 'zuckerberg'), 'openai': ('openai', 'chatgpt'), 'google': ('google', 'alphabet'), 'apple': ('apple', 'iphone'), 'microsoft': ('microsoft', 'windows', 'xbox'), 'nvidia': ('nvidia', 'geforce', 'rtx'), 'amazon': ('amazon', 'aws'), 'walmart': ('walmart', 'wal-mart')}

def subject_keys(item):
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    return [subject for subject, aliases in SUBJECT_ALIASES.items()
            if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases)]


def topic_key(item):
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    groups = [
        ("military-conflict", ("war", "airstrike", "missile", "troops", "invasion", "ceasefire", "military conflict")),
        ("recall-food-safety", ("recall", "recalled", "food safety", "contamination", "salmonella", "listeria", "eggs", "egg")),
        ("disaster-weather", ("earthquake", "hurricane", "tornado", "wildfire", "flood", "drought")),
        ("crime-public-safety", ("shooting", "killed", "murder", "police", "arrested", "missing")),
        ("economy-markets", ("inflation", "recession", "stocks", "market", "tariff", "oil prices", "unemployment")),
        ("government-politics", ("congress", "senate", "supreme court", "executive order", "election", "white house")),
        ("technology", ("ai", "artificial intelligence", "cyberattack", "hack", "software", "chip", "technology")),
        ("business", ("company", "acquisition", "layoffs", "bankruptcy", "earnings", "ceo")),
        ("science-space", ("nasa", "space", "rocket", "scientists", "study", "research")),
        ("sports", ("nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball")),
    ]
    for topic, terms in groups:
        if any(term in text for term in terms): return topic
    return "general"


def article_terms(item):
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    words = re.findall(r"[a-z0-9]+", text)
    stop = {"the","a","an","and","or","but","for","from","with","into","over","after","before","about","amid","during","this","that","these","those","says","said","say","new","news","latest","update","updates","report","reports","reported","according","officials","official","will","could","would","may","can","has","have","had","was","were","are","is","be","been","being","to","of","in","on","at","by","as","it","its","their","they","them","who","what","when","where","why","how","us","one","two","first","second","third","today","now","more","just","also","still","amid"}
    out=set()
    for w in words:
        if len(w)<3 or w in stop: continue
        if w.endswith('ies') and len(w)>4: w=w[:-3]+'y'
        elif w.endswith('s') and not w.endswith('ss') and len(w)>4: w=w[:-1]
        out.add(w)
    return out


def same_event_topic(a, b):
    """Detect redundant coverage of the same real-world event without collapsing a whole subject."""
    ta, tb = article_terms(a), article_terms(b)
    shared = ta & tb
    sa, sb = set(subject_keys(a)), set(subject_keys(b))
    shared_subjects = sa & sb
    topic_a, topic_b = topic_key(a), topic_key(b)

    # Title terms are more useful for event matching than long publisher descriptions.
    title_a = set(re.findall(r"[a-z0-9]+", (a.get('title') or '').lower()))
    title_b = set(re.findall(r"[a-z0-9]+", (b.get('title') or '').lower()))
    title_stop = {"the","a","an","and","or","but","for","from","with","into","over","after","before","about","amid","during","this","that","these","those","says","said","new","news","latest","update","report","reported","according","officials","official","will","could","would","may","can","has","have","had","was","were","are","is","be","been","to","of","in","on","at","by","as","it","its","their","they","them","who","what","when","where","why","how","us","one","two","first","second","third","today","now","more","just","also","still"}
    title_a = {w for w in title_a if len(w) >= 3 and w not in title_stop}
    title_b = {w for w in title_b if len(w) >= 3 and w not in title_stop}
    title_shared = title_a & title_b

    # Strong phrase/event anchors. These distinguish an actual event from a broad subject.
    event_groups = {
        'military': {'war','warfare','siege','airstrike','airstrikes','missile','missiles','strike','strikes','bombing','bombed','troops','invasion','invades','invaded','ceasefire','fighting','battle','battles','offensive','attack','attacks','attacked','retaliation','retaliates','retaliatory','shelling','raid','raids'},
        'recall': {'recall','recalls','recalled','contamination','contaminated','salmonella','listeria','outbreak','outbreaks','safety'},
        'disaster': {'earthquake','hurricane','tornado','wildfire','flood','flooding','landslide','eruption','evacuation','evacuations'},
        'crime': {'shooting','shootings','murder','murdered','homicide','arrest','arrested','missing','kidnapped','robbery','stabbing','stabbings','charged','indicted'},
        'government': {'bill','bills','vote','votes','voted','law','lawsuit','ruling','rules','ruled','order','orders','executive','legislation','hearing','hearings','impeach','impeachment'},
        'business': {'acquisition','acquires','acquired','merger','merges','layoffs','laid','bankruptcy','bankrupt','closure','closes','closed','earnings','recall'},
        'technology': {'breach','hack','hacked','hackers','outage','outages','vulnerability','vulnerabilities','launch','launches','launched','shutdown','shuts','updates','update'},
        'sports': {'game','games','match','matches','injury','injured','trade','trades','signed','signs','score','scores','playoffs','championship'},
    }

    def event_groups_for(terms):
        return {name for name, words in event_groups.items() if terms & words}

    groups_a = event_groups_for(ta | title_a)
    groups_b = event_groups_for(tb | title_b)
    shared_groups = groups_a & groups_b

    # Exact/near-exact lexical overlap remains the safest signal.
    if len(shared) >= 4:
        return True
    if len(shared) >= 3 and len(shared) / max(1, len(ta | tb)) >= 0.24:
        return True
    if len(title_shared) >= 3:
        return True

    # Same named subject + same event class + at least one meaningful event anchor.
    # This catches examples like "war in Iran" / "Iran under siege" while allowing
    # unrelated Iran stories such as sanctions, diplomacy, or elections to coexist.
    if shared_subjects and shared_groups:
        if len(title_shared) >= 1 and len(shared) >= 1:
            return True
        if len(shared) >= 2:
            return True

    # If titles share a named subject and two event-specific words, treat as one event
    # even when descriptions use different wording.
    if shared_subjects and len(title_shared) >= 2 and shared_groups:
        return True

    # Recall/safety stories commonly use different wording ("recalls eggs" vs
    # "national egg recall"). Two shared terms plus the same event class is enough.
    if topic_a == topic_b and topic_a in {'recall-food-safety','disaster-weather','crime-public-safety'}:
        if len(shared) >= 2 and (shared_groups or len(title_shared) >= 1):
            return True

    return False


def attach_related(primary, related):
    if key(primary)==key(related): return
    related_list=primary.setdefault('_relatedArticles', [])
    if any(key(x)==key(related) for x in related_list): return
    related_list.append(related)
    primary['_relatedArticles']=related_list[:4]
















































































































































def select_top_stories(unique):
    """Rank distinct news events first, then retain a diverse rotating Top Stories pool."""
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)

    # Build event clusters before scoring. Multi-outlet coverage is therefore a
    # property of the event, not of one URL/headline key.
    ordered = sorted(
        unique,
        key=lambda item: (impact_score(item, newest_time), item["published"]),
        reverse=True,
    )
    clusters = []
    for item in ordered:
        match = None
        for cluster in clusters:
            # Compare against a few members so differently worded follow-ups can
            # join the same event without letting one broad topic swallow others.
            if any(same_event_topic(member, item) for member in cluster[:4]):
                match = cluster
                break
        if match is None:
            clusters.append([item])
        else:
            match.append(item)

    ranked = []
    for cluster_id, cluster in enumerate(clusters):
        representative = max(
            cluster,
            key=lambda item: (impact_score(item, newest_time), item["published"]),
        )
        source_set = {
            source_key(item.get("source") or "Unknown")
            for item in cluster
            if source_key(item.get("source") or "Unknown")
        }
        outlet_count = max(1, len(source_set))
        coverage_boost = min(36, max(0, outlet_count - 1) * 9) + (8 if outlet_count >= 4 else 0)
        score = impact_score(representative, newest_time) + coverage_boost

        # Related coverage prefers distinct publishers first, then the newest
        # remaining reports. This makes the coverage drawer more useful.
        related_candidates = sorted(
            [item for item in cluster if key(item) != key(representative)],
            key=lambda item: item["published"],
            reverse=True,
        )
        seen_related_sources = {source_key(representative.get("source") or "Unknown")}
        deferred = []
        for related in related_candidates:
            src = source_key(related.get("source") or "Unknown")
            if src and src not in seen_related_sources:
                attach_related(representative, related)
                seen_related_sources.add(src)
            else:
                deferred.append(related)
            if len(representative.get('_relatedArticles', [])) >= 4:
                break
        if len(representative.get('_relatedArticles', [])) < 4:
            for related in deferred:
                attach_related(representative, related)
                if len(representative.get('_relatedArticles', [])) >= 4:
                    break

        ranked.append((score, representative["published"], outlet_count, cluster_id, representative))

    ranked.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    selected = []
    selected_clusters = set()
    seen_keys = set()
    source_counts = {}
    subject_counts = {}
    topic_counts = {}
    TOP_POOL_SIZE = 60
    VISIBLE_WINDOW = 10
    VISIBLE_SOURCE_CAP = 2
    SUBJECT_CAP = 4
    TOPIC_CAP = 8
    MAX_PER_SOURCE = 5

    def can_select(item, cluster_id, source_cap, enforce_topics=True):
        k = key(item)
        src = source_key(item.get("source") or "Unknown")
        if not k or k in seen_keys or cluster_id in selected_clusters:
            return False
        if source_counts.get(src, 0) >= source_cap:
            return False
        if enforce_topics:
            subs = subject_keys(item)
            topic = topic_key(item)
            if subs and max(subject_counts.get(x, 0) for x in subs) >= SUBJECT_CAP:
                return False
            if topic_counts.get(topic, 0) >= TOPIC_CAP:
                return False
        return True

    def add_item(item, cluster_id):
        k = key(item)
        src = source_key(item.get("source") or "Unknown")
        subs = subject_keys(item)
        topic = topic_key(item)
        selected.append(item)
        selected_clusters.add(cluster_id)
        seen_keys.add(k)
        source_counts[src] = source_counts.get(src, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        for sub in subs:
            subject_counts[sub] = subject_counts.get(sub, 0) + 1

    # The first screen should not be dominated by one publisher.
    for _, _, _, cluster_id, item in ranked:
        if len(selected) >= VISIBLE_WINDOW:
            break
        if can_select(item, cluster_id, VISIBLE_SOURCE_CAP, True):
            add_item(item, cluster_id)

    # If an unusually small source pool prevents ten stories, fill the visible
    # window while preserving the normal whole-pool source cap.
    if len(selected) < VISIBLE_WINDOW:
        for _, _, _, cluster_id, item in ranked:
            if len(selected) >= VISIBLE_WINDOW:
                break
            if can_select(item, cluster_id, MAX_PER_SOURCE, True):
                add_item(item, cluster_id)

    # Fill the deeper rotation while preserving subject/topic and source variety.
    for _, _, _, cluster_id, item in ranked:
        if len(selected) >= TOP_POOL_SIZE:
            break
        if can_select(item, cluster_id, MAX_PER_SOURCE, True):
            add_item(item, cluster_id)

    # Final fallback only relaxes topic caps; event and publisher caps remain.
    if len(selected) < TOP_POOL_SIZE:
        for _, _, _, cluster_id, item in ranked:
            if len(selected) >= TOP_POOL_SIZE:
                break
            if can_select(item, cluster_id, MAX_PER_SOURCE, False):
                add_item(item, cluster_id)

    related_count = sum(len(x.get('_relatedArticles', [])) for x in selected)
    print(
        'TOP event clusters: '
        + str(len(clusters))
        + ' events ranked; '
        + str(related_count)
        + ' related article(s) attached; '
        + str(len(selected))
        + ' rotating Top Stories retained.'
    )
    return selected


def underreported_topic(item):
    text = f"{item.get('title','')} {item.get('description','')}".lower()
    groups = [
        ("legislation-policy", ("bill", "legislation", "law", "executive order", "regulation", "rule", "ordinance")),
        ("government-accountability", ("audit", "inspector general", "ethics", "misconduct", "oversight", "watchdog", "records request")),
        ("healthcare", ("hospital", "medicaid", "medicare", "health care", "healthcare", "drug price", "nursing home")),
        ("environment-water", ("water", "contamination", "pollution", "toxic", "climate", "drought", "environment")),
        ("labor-workers", ("workers", "labor", "union", "wage", "workplace", "strike", "overtime")),
        ("civil-rights", ("civil rights", "voting rights", "discrimination", "disability rights", "lgbt", "tribal rights")),
        ("privacy-surveillance", ("privacy", "surveillance", "facial recognition", "data broker", "tracking", "spying")),
        ("criminal-justice", ("prison", "jail", "policing", "police misconduct", "sentencing", "prosecutor", "criminal justice")),
        ("education", ("school", "student", "teacher", "education", "college", "university")),
        ("infrastructure", ("bridge", "road", "infrastructure", "power grid", "utility", "broadband")),
        ("indigenous", ("tribal", "tribe", "navajo", "indigenous", "native american")),
        ("consumer", ("consumer", "recall", "fraud", "scam", "fees", "insurance", "product safety")),
        ("military-veterans", ("veteran", "va ", "pentagon", "military", "service member", "troops")),
        ("science-public-health", ("research", "study", "disease", "outbreak", "public health", "science")),
        ("corporate-accountability", ("company", "corporate", "antitrust", "monopoly", "layoffs", "bankruptcy", "whistleblower")),
        ("international-human-impact", ("refugee", "famine", "humanitarian", "war crimes", "displaced", "aid")),
    ]
    for topic, terms in groups:
        if any(term in text for term in terms):
            return topic
    return topic_key(item)


def underreported_source_allowed(item):
    source = source_key(item.get('source') or '')
    raw = (item.get('source') or '').lower()
    title = (item.get('title') or '').lower()
    if any(token.replace(' ','') in source or token in raw for token in UNDERREPORTED_PAYWALL_SOURCE_TOKENS):
        return False
    ceremonial = ('patriot day', 'proclamation', 'personal vision', 'historic results', 'promises made', 'remarks by', 'statement from the president')
    if any(term in title for term in ceremonial):
        return False
    government_source = any(term in raw for term in ('white house', 'congress.gov', 'congress gov', 'federal register', '.gov'))
    accountability_or_action = any(term in title for term in (
        'audit', 'report', 'investigation', 'inspector general', 'enforcement', 'settlement',
        'bill', 'act', 'law', 'resolution', 'executive order', 'final rule', 'proposed rule',
        'regulation', 'ordinance', 'veto', 'passes', 'passed', 'signed'
    ))
    if government_source and not accountability_or_action:
        return False
    if 'congress' in raw:
        years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', title)]
        current_year = datetime.now(timezone.utc).year
        if years and min(years) < current_year - 2:
            return False
    return True


def legislation_action_allowed(item):
    title = (item.get('title') or '').lower()
    source = (item.get('source') or '').lower()
    padded = f" {title} "

    # Never treat promotional/ceremonial pages or generic pre-publication queues
    # as legislation news, even when their titles happen to mention a bill.
    reject_always = (
        'public inspection:', 'personal vision', 'historic results',
        'promises made', 'patriot day', 'proclamation', 'remarks by',
        'statement from the president', 'fact sheet: president',
    )
    if any(term in title for term in reject_always):
        return False

    # Bare profile and amendment/database entries are not useful cards without
    # an explanatory action headline.
    if title.startswith(('representative ', 'senator ', 'text - ', 'actions - ')):
        return False
    if re.match(r'^s\.amdt\.\d+\s+to\s+', title):
        return False

    years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', title)]
    current_year = datetime.now(timezone.utc).year
    if years and min(years) < current_year - 2 and ('congress' in source or 'federal register' in source):
        return False

    explicit_action = any(term in padded for term in (
        ' signed into law ', ' signs bill ', ' signed bill ', ' enacted ',
        ' passes house ', ' house passes ', ' passes senate ', ' senate passes ',
        ' passed the house ', ' passed the senate ', ' vetoed ', ' vetoes ',
        ' executive order ', ' final rule ', ' proposed rule ', ' rulemaking ',
        ' rescission ', ' repeal ', ' ordinance ', ' resolution '
    ))
    if explicit_action:
        return True

    # Established journalism may surface an introduced/proposed measure before
    # the official database shows a clear status; keep it if the headline is
    # explicitly about legislation/regulation.
    government_source = any(term in source for term in (
        'congress.gov','congress gov','federal register','white house','.gov','nmlegis'
    ))
    measure_terms = (' bill ', ' h.r.', ' s.', ' act ', ' legislation ', ' regulation ', ' ordinance ')
    if not government_source and any(term in padded for term in measure_terms):
        return True

    # Raw government pages are retained only for measures with broad public
    # consequence. This avoids filling the tab with obscure naming/site bills.
    high_impact = any(term in padded for term in (
        ' war powers ', ' military ', ' national security ', ' veterans ',
        ' medicaid ', ' medicare ', ' health care ', ' healthcare ', ' hospital ',
        ' tax ', ' taxes ', ' budget ', ' spending ', ' housing ',
        ' immigration ', ' border ', ' asylum ', ' voting ', ' election ',
        ' civil rights ', ' privacy ', ' surveillance ', ' cybersecurity ',
        ' artificial intelligence ', ' antitrust ', ' labor ', ' wage ', ' workers ',
        ' education ', ' student ', ' abortion ', ' environment ', ' pollution ',
        ' water ', ' climate ', ' energy ', ' consumer ', ' disability ', ' tribal ', ' indigenous '
    ))
    if government_source and high_impact and any(term in padded for term in measure_terms):
        return True

    # Substantive Federal Register rules can be useful even without the literal
    # phrase "final rule," but routine notices and information collections are not.
    if 'federal register' in source:
        if any(term in title for term in ('information collection', 'combined filings', 'postal products', 'meeting notice', 'availability of')):
            return False
        return high_impact and any(term in title for term in (
            'requirements', 'standards', 'eligibility', 'registration', 'fee for',
            'ban on', 'regulation of', 'amendments to', 'rule on', 'rules for'
        ))
    return False


def legislation_score(item, newest_time):
    title = (item.get('title') or '').lower()
    source = (item.get('source') or '').lower()
    score = impact_score(item, newest_time)
    if any(term in title for term in ('signed into law','signed bill','enacted','veto')): score += 34
    elif any(term in title for term in ('passes house','house passes','passes senate','senate passes','passed the house','passed the senate')): score += 30
    elif 'executive order' in title: score += 28
    elif 'final rule' in title: score += 25
    elif any(term in title for term in ('proposed rule','regulation','rescission','repeal')): score += 20
    else: score += 12
    if any(term in title for term in ('new mexico','farmington','san juan county','durango','cortez')): score += 22
    if any(term in source for term in ('source new mexico','new mexico in depth','searchlight new mexico','tri-city record','durango herald','the journal')): score += 12
    return score


def select_legislation_stories(items, limit=30):
    valid = [item for item in items if legislation_action_allowed(item)]
    if not valid:
        return []
    newest_time = max(x['published'] for x in valid)
    ranked = sorted(valid, key=lambda x: (legislation_score(x, newest_time), x['published']), reverse=True)
    selected=[]; seen=set(); source_counts={}
    for item in ranked:
        k=key(item); src=source_key(item.get('source') or 'Unknown')
        if not k or k in seen or source_counts.get(src,0) >= 5:
            continue
        related = next((prior for prior in selected if same_event_topic(prior,item)), None)
        if related is not None:
            attach_related(related,item); continue
        selected.append(item); seen.add(k); source_counts[src]=source_counts.get(src,0)+1
        if len(selected)>=limit: break
    return selected


def select_underreported(unique):
    """Select high-impact, low-saturation public-interest stories with strong topic diversity."""
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)
    candidates = []
    for item in unique:
        if not underreported_source_allowed(item):
            continue
        src_raw = (item.get('source') or '').lower()
        impact = impact_score(item, newest_time)
        text = f"{item.get('title','')} {item.get('description','')}".lower()
        public_interest_bonus = 12 if any(t in src_raw for t in UNDERREPORTED_PUBLIC_INTEREST_TOKENS) else 0
        public_interest_bonus += 8 if any(t in text for t in (
            'investigation','audit','inspector general','whistleblower','public records','lawsuit','settlement',
            'contamination','pollution','hospital','medicaid','workers','labor','privacy','surveillance',
            'civil rights','tribal','indigenous','veteran','fraud','regulation','legislation','bill','law'
        )) else 0
        substantive_signal = any(t in text for t in (
            'investigation','audit','inspector general','whistleblower','public records','lawsuit','settlement',
            'contamination','pollution','hospital','medicaid','workers','labor','privacy','surveillance',
            'civil rights','tribal','indigenous','veteran','fraud','regulation','legislation','bill','law',
            'court','ruling','election','voting','killed','deaths','war','attack','strike','famine','humanitarian',
            'wildfire','drought','flood','outbreak','recall','bankruptcy','layoffs','school','education','housing'
        ))
        public_interest_source = any(t in src_raw for t in UNDERREPORTED_PUBLIC_INTEREST_TOKENS)
        if not substantive_signal and not public_interest_source:
            continue
        celebrity_penalty = 10 if any(t in text for t in ('donald trump','president trump','elon musk')) and public_interest_bonus < 12 else 0
        score = impact + public_interest_bonus - celebrity_penalty
        if score < 24:
            continue
        candidates.append((score, item["published"], item))
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    selected = []
    seen_keys = set()
    source_counts = {}
    subject_counts = {}
    topic_counts = {}
    for _, _, item in candidates:
        k = key(item)
        src = source_key(item.get('source') or 'Unknown')
        subs = subject_keys(item)
        topic = underreported_topic(item)
        first_page = len(selected) < 10
        subject_cap = 1 if first_page else 2
        topic_cap = 1 if first_page else 4
        if not k or k in seen_keys or source_counts.get(src, 0) >= 2:
            continue
        if subs and max(subject_counts.get(x, 0) for x in subs) >= subject_cap:
            continue
        if topic_counts.get(topic, 0) >= topic_cap:
            continue
        related = next((prior for prior in selected if same_event_topic(prior, item)), None)
        if related is not None:
            attach_related(related, item)
            continue
        selected.append(item)
        seen_keys.add(k)
        source_counts[src] = source_counts.get(src, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        for sub in subs:
            subject_counts[sub] = subject_counts.get(sub, 0) + 1
        if len(selected) >= 30:
            break
    print('Underreported diversity: ' + str(len(selected)) + ' stories across ' + str(len(topic_counts)) + ' topic buckets.')
    return selected


def select_category_stories(items, limit=30):
    """Select up to 30 distinct stories, with Local queries treated as the geographic scope."""
    if items and items[0].get("category") == "legislation":
        return select_legislation_stories(items, limit=limit)
    if items and items[0].get("category") == "local":
        local_terms = (
            "farmington", "san juan county", "aztec", "bloomfield", "kirtland",
            "shiprock", "navajo nation", "four corners", "san juan basin",
            "durango", "la plata county", "bayfield", "ignacio",
            "cortez", "montezuma county", "mancos", "dolores",
            "gallup", "mckinley county", "window rock", "chinle", "kayenta",
            "blanding", "monticello", "san juan county utah",
        )
        reject_terms = (
            "kirtland afb", "kirtland air force base",
        )
        local_items = []
        for item in items:
            title = (item.get("title") or "").lower()
            desc = (item.get("description") or "").lower()
            searchable = f"{title} {desc}"
            if any(term in searchable for term in reject_terms):
                continue
            if any(term in searchable for term in local_terms):
                local_items.append(item)
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


def select_region_stories(items, per_state=8, limit=80):
    ranked = sorted(items, key=lambda x: x["published"], reverse=True)
    selected, seen = [], set()
    states = []
    for item in ranked:
        state = (item.get("state") or "").strip()
        if state and state not in states:
            states.append(state)
    for state in states:
        state_items = [item for item in ranked if (item.get("state") or "").strip() == state]
        for item in select_category_stories(state_items, limit=per_state):
            k = key(item)
            if not k or k in seen:
                continue
            selected.append(item); seen.add(k)
            if len(selected) >= limit:
                return selected
    for item in ranked:
        k = key(item)
        if not k or k in seen:
            continue
        selected.append(item); seen.add(k)
        if len(selected) >= limit:
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
        out += ["<item>", f'<title>{xml_escape(item["title"])}</title>', f'<link>{xml_escape(item["link"])}</link>', f'<description>{xml_escape(item.get("description", ""))}</description>', f'<pubDate>{xml_escape(item["pubDate"])}</pubDate>', f'<source>{xml_escape(item["source"])}</source>', f'<category>{item["category"]}</category>', f'<region>{xml_escape(item.get("region", ""))}</region>', f'<state>{xml_escape(item.get("state", ""))}</state>', f'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>']
        related=item.get('_relatedArticles', [])
        if related:
            out.append('<relatedArticles>')
            for rel in related:
                out += [f'<article><title>{xml_escape(rel.get("title",""))}</title>', f'<link>{xml_escape(rel.get("link",""))}</link>', f'<source>{xml_escape(rel.get("source",""))}</source></article>']
            out.append('</relatedArticles>')
        out += [f'<guid isPermaLink="false">{guid}</guid>', "</item>"]
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


def main():
    all_items = []
    for category, query in QUERIES.items():
        try:
            if category == "local":
                items = []
                worker_count = max(1, min(6, len(LOCAL_QUERIES)))
                with ThreadPoolExecutor(max_workers=worker_count) as pool:
                    jobs = {pool.submit(fetch, local_query): local_query for local_query in LOCAL_QUERIES}
                    for job in as_completed(jobs):
                        local_query = jobs[job]
                        try:
                            batch = parse_items(job.result(), category)
                            print(f"local/{local_query}: {len(batch)} fresh stories")
                            items.extend(batch)
                        except Exception as exc:
                            print(f"Local feed failed for {local_query}: {exc}")
                usable_count = len(select_category_stories(items, limit=30))
                target = CATEGORY_POOL_MINIMUMS.get("local", 20)
                if usable_count < target:
                    for fallback_source, fallback_query in TRUSTED_CATEGORY_FALLBACKS.get("local", []):
                        try:
                            batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                            items.extend(batch)
                            usable_count = len(select_category_stories(items, limit=30))
                            print(f"local fallback/{fallback_source}: {len(batch)} accepted; {usable_count} usable local stories")
                            if usable_count >= target:
                                break
                        except Exception as exc:
                            print(f"Local fallback failed for {fallback_source}: {exc}")
            elif category == "region":
                items = []
                for region_name, region_queries in query.items():
                    region_count = 0
                    for region_query in region_queries:
                        try:
                            batch = parse_items(fetch(region_query), category)
                            for item in batch:
                                item["region"] = region_name
                                item["state"] = region_query_state(region_query)
                            region_count += len(batch)
                            items.extend(batch)
                        except Exception as exc:
                            print(f"Region feed failed for {region_name}/{region_query}: {exc}")
                    print(f"region/{region_name}: {region_count} fresh stories")
            else:
                if category in ("federal", "legislation") and isinstance(query, list):
                    items = []
                    for federal_query in query:
                        try:
                            batch = parse_items(fetch(federal_query), category)
                            items.extend(batch)
                            print(f"{category}/{federal_query}: {len(batch)} fresh stories")
                        except Exception as exc:
                            print(f"{category.title()} feed failed for {federal_query}: {exc}")
                else:
                    combined_query = " OR ".join(f"({q})" for q in query) if isinstance(query, list) else query
                    items = parse_items(fetch(combined_query), category)
                own_count = sum(1 for item in items if item.get("category") == category)
                usable_count = len(select_category_stories(items, limit=30)) if category == "local" else own_count
                if category in TRUSTED_CATEGORY_FALLBACKS and usable_count < CATEGORY_POOL_MINIMUMS.get(category, 10):
                    for fallback_source, fallback_query in TRUSTED_CATEGORY_FALLBACKS[category]:
                        try:
                            batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                            items.extend(batch)
                            own_count = sum(1 for item in items if item.get("category") == category)
                            usable_count = len(select_category_stories(items, limit=30)) if category == "local" else own_count
                            print(f"{category} fallback/{fallback_source}: {len(batch)} accepted; {usable_count} usable category stories")
                            target = CATEGORY_POOL_MINIMUMS.get(category, 20)
                            if usable_count >= target and category not in ("gaming", "technology"):
                                break
                        except Exception as exc:
                            print(f"{category} fallback failed for {fallback_source}: {exc}")
            if category == "legislation":
                for fallback_source, fallback_query in LEGISLATION_JOURNALISM_QUERIES:
                    try:
                        batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                        items.extend(batch)
                        print(f"legislation journalism/{fallback_source}: {len(batch)} fresh stories")
                    except Exception as exc:
                        print(f"Legislation journalism failed for {fallback_source}: {exc}")
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

    underreported_discovery_items = []
    for source_name, query in UNDERREPORTED_DISCOVERY_QUERIES:
        try:
            discovered = parse_items(fetch(query), "us", source_override=source_name)
            underreported_discovery_items.extend(discovered)
            print(f"underreported/{source_name}: {len(discovered)} fresh public-interest stories")
        except Exception as exc:
            print(f"Underreported discovery failed for {source_name}: {exc}")

    seen, unique = set(), []
    for item in sorted(all_items, key=lambda x: x["published"], reverse=True):
        k = key(item)
        category_key = item.get("category") or "world"
        scoped_key = (category_key, k)
        if not k or scoped_key in seen:
            continue
        seen.add(scoped_key); unique.append(item)

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
                selected_by_category[category].extend(select_region_stories(region_items, per_state=8, limit=80))
        else:
            selected_by_category[category] = select_category_stories(category_items)
    top = select_top_stories(top_unique)
    underreported = select_underreported(unique + underreported_discovery_items)

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
