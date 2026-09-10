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
    "new mexico in depth", "capital and main", "the 19th", "route fifty",
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
'''
needle = 'TRUSTED_SOURCE_TOKENS = tuple(sorted(set(TRUSTED_SOURCE_TOKENS) | set(TRUSTED_SPORTS_SOURCE_TOKENS)))\n'
if 'UNDERREPORTED_DISCOVERY_QUERIES' not in s:
    if needle not in s:
        raise SystemExit('Could not locate trusted source insertion point')
    s = s.replace(needle, needle + trusted_add, 1)
elif 'LEGISLATION_JOURNALISM_QUERIES' not in s:
    anchor = 'UNDERREPORTED_PAYWALL_SOURCE_TOKENS = ('
    pos = s.find(anchor)
    if pos < 0:
        raise SystemExit('Could not locate Underreported source constants')
    extra = '''LEGISLATION_JOURNALISM_QUERIES = [
    ("Source New Mexico", "site:sourcenm.com (bill OR legislature OR law OR regulation OR executive order) New Mexico"),
    ("New Mexico In Depth", "site:nmindepth.com (bill OR legislature OR law OR regulation) New Mexico"),
    ("Searchlight New Mexico", "site:searchlightnm.org (bill OR law OR legislature OR regulation) New Mexico"),
    ("Tri-City Record", "site:tricityrecordnm.com (ordinance OR city council OR county commission OR law) Farmington"),
    ("Durango Herald", "site:durangoherald.com (ordinance OR city council OR county commission OR law) Durango"),
    ("The Journal", "site:the-journal.com (ordinance OR city council OR county commission OR law) Cortez"),
]

'''
    s = s[:pos] + extra + s[pos:]

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
    title = (item.get('title') or '').lower()
    if any(token.replace(' ','') in source or token in raw for token in UNDERREPORTED_PAYWALL_SOURCE_TOKENS):
        return False
    # Ceremonial/promotional government pages are not underreported journalism.
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
    # Google can surface archival Congress.gov pages as if they were new; reject obviously old measures.
    if 'congress' in raw:
        years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', title)]
        current_year = datetime.now(timezone.utc).year
        if years and min(years) < current_year - 2:
            return False
    return True


def legislation_action_allowed(item):
    title = (item.get('title') or '').lower()
    source = (item.get('source') or '').lower()
    if any(term in title for term in (
        'public inspection: combined filings', 'public inspection: new postal products',
        'personal vision', 'historic results', 'promises made, promises kept',
        'patriot day', 'proclamation', 'remarks by', 'representative ', 'senator '
    )):
        # A representative/senator page can survive only when the headline is explicitly about a measure/action.
        if not any(term in title for term in (' bill ', ' h.r.', ' s.', ' act ', ' resolution ', 'passes', 'passed', 'signed', 'veto')):
            return False
    years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', title)]
    current_year = datetime.now(timezone.utc).year
    if years and min(years) < current_year - 2 and ('congress' in source or 'federal register' in source):
        return False
    strong_actions = (
        'signed into law', 'signs bill', 'signed bill', 'enacted', 'passes house', 'house passes',
        'passes senate', 'senate passes', 'passed the house', 'passed the senate', 'veto',
        'executive order', 'final rule', 'proposed rule', 'rulemaking', 'regulation', 'rescission',
        'repeal', 'ordinance', 'amendment', 'resolution', 'legislation', ' bill ', ' h.r.', ' s.'
    )
    if any(term in f' {title} ' for term in strong_actions):
        return True
    if 'federal register' in source and any(term in title for term in (
        'requirements', 'standards', 'eligibility', 'registration', 'fee for', 'ban on',
        'regulation of', 'amendments to', 'rule on', 'rules for'
    )):
        return True
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
    selected=[]; seen=set(); source_counts={}; event_counts={}
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
pattern = re.compile(r'def underreported_topic\(item\):.*?\n\ndef select_category_stories', re.S)
if pattern.search(s):
    s = pattern.sub(selector + '\n\ndef select_category_stories', s, count=1)
else:
    pattern = re.compile(r'def select_underreported\(unique\):.*?\n\ndef select_category_stories', re.S)
    s, n = pattern.subn(selector + '\n\ndef select_category_stories', s, count=1)
    if n != 1:
        raise SystemExit('Could not replace Underreported/legislation selectors')

# Route legislation through its strict action selector instead of generic news selection.
needle = '''def select_category_stories(items, limit=30):
    """Select up to 30 distinct stories, with Local queries treated as the geographic scope."""
'''
replacement = needle + '''    if items and items[0].get("category") == "legislation":
        return select_legislation_stories(items, limit=limit)
'''
if needle in s and 'return select_legislation_stories(items, limit=limit)' not in s:
    s = s.replace(needle, replacement, 1)

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

# Always supplement legislation with established NM/Four Corners journalism;
# the official federal feeds are numerous enough that a threshold-based fallback would never run.
marker = '            print(f"{category}: {len(items)} fresh stories before dedupe")'
if 'legislation journalism/{fallback_source}' not in s and marker in s:
    add = '''            if category == "legislation":
                for fallback_source, fallback_query in LEGISLATION_JOURNALISM_QUERIES:
                    try:
                        batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                        items.extend(batch)
                        print(f"legislation journalism/{fallback_source}: {len(batch)} fresh stories")
                    except Exception as exc:
                        print(f"Legislation journalism failed for {fallback_source}: {exc}")
'''
    s = s.replace(marker, add + marker, 1)

P.write_text(s, encoding='utf-8')
print('Applied diverse public-interest Underreported selection and strict, action-focused Laws & Legislation collection.')
