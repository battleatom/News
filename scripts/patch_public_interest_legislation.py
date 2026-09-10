from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')

# Add legislation as a first-class feed category.
s = s.replace(
    'SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "nm", "local", "region", "nfl", "technology", "gaming", "military"]',
    'SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "legislation", "nm", "local", "region", "nfl", "technology", "gaming", "military"]',
    1,
)

if '    "legislation": [' not in s:
    anchor = '    "nm": "New Mexico government OR New Mexico news",\n'
    block = '''    "legislation": [
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
'''
    if anchor not in s:
        raise SystemExit('Could not locate QUERIES insertion point')
    s = s.replace(anchor, block + anchor, 1)

# Expand trusted public-interest / primary-government reporting sources.
trusted_add = '''
PUBLIC_INTEREST_SOURCE_TOKENS = (
    "propublica", "the marshall project", "kff health news", "kaiser health news",
    "inside climate news", "insideclimate news", "grist", "reveal", "center for public integrity",
    "source new mexico", "searchlight new mexico", "stateline", "states newsroom",
    "new mexico in depth", "capital and main", "the 19th", "route fifty", "route fifty",
    "congress gov", "congress.gov", "federal register", "federalregister.gov",
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
'''
needle = 'TRUSTED_SOURCE_TOKENS = tuple(sorted(set(TRUSTED_SOURCE_TOKENS) | set(TRUSTED_SPORTS_SOURCE_TOKENS)))\n'
if 'UNDERREPORTED_DISCOVERY_QUERIES' not in s:
    if needle not in s:
        raise SystemExit('Could not locate trusted source insertion point')
    s = s.replace(needle, needle + trusted_add, 1)

# Legislation matters strongly for public-interest ranking.
s = s.replace(
    'CATEGORY_WEIGHT = {"world": 18, "us": 22, "presidential": 24, "federal": 22,',
    'CATEGORY_WEIGHT = {"world": 18, "us": 22, "presidential": 24, "federal": 22, "legislation": 24,',
    1,
)

selector = r'''def underreported_topic(item):
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
    if any(token.replace(' ','') in source or token in raw for token in UNDERREPORTED_PAYWALL_SOURCE_TOKENS):
        return False
    return True


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
        # Famous-person coverage is allowed, but fame alone should not make something underreported.
        celebrity_penalty = 8 if any(t in text for t in ('donald trump','president trump','elon musk')) and public_interest_bonus < 12 else 0
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
        topic_cap = 2 if first_page else 4
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
'''
pattern = re.compile(r'def select_underreported\(unique\):.*?\n\ndef select_category_stories', re.S)
s, n = pattern.subn(selector + '\n\ndef select_category_stories', s, count=1)
if n != 1:
    raise SystemExit('Could not replace select_underreported()')

# Fetch public-interest journalism exclusively for Underreported discovery.
if 'underreported_discovery_items = []' not in s:
    anchor = '    seen, unique = set(), []\n'
    discovery = '''    underreported_discovery_items = []
    for source_name, query in UNDERREPORTED_DISCOVERY_QUERIES:
        try:
            discovered = parse_items(fetch(query), "us", source_override=source_name)
            underreported_discovery_items.extend(discovered)
            print(f"underreported/{source_name}: {len(discovered)} fresh public-interest stories")
        except Exception as exc:
            print(f"Underreported discovery failed for {source_name}: {exc}")

'''
    if anchor not in s:
        raise SystemExit('Could not locate discovery insertion point')
    s = s.replace(anchor, discovery + anchor, 1)

s = s.replace('underreported = select_underreported(unique)', 'underreported = select_underreported(unique + underreported_discovery_items)', 1)

# Fetch each legislation query separately, as with Federal, so one giant query cannot starve subtopics.
s = s.replace(
    'if category == "federal" and isinstance(query, list):',
    'if category in ("federal", "legislation") and isinstance(query, list):',
    1,
)
s = s.replace('print(f"federal/{federal_query}: {len(batch)} fresh stories")', 'print(f"{category}/{federal_query}: {len(batch)} fresh stories")', 1)
s = s.replace('print(f"Federal feed failed for {federal_query}: {exc}")', 'print(f"{category.title()} feed failed for {federal_query}: {exc}")', 1)

P.write_text(s, encoding='utf-8')
print('Applied public-interest Underreported diversity and Laws & Legislation collection.')
