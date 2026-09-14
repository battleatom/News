import difflib
import hashlib
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NEWS = Path('News')
MAX_TECH = 90
MAX_GAMING = 90
MAX_US = 90

TECH_QUERIES = [
    'technology AI cybersecurity chips devices',
    'Apple Google Microsoft Nvidia AMD Intel technology',
    'OpenAI Anthropic AI model technology',
    'cybersecurity data breach ransomware technology',
    'semiconductor chip Nvidia AMD Intel technology',
    'smartphone laptop Android iPhone technology',
    'robotics quantum computing technology',
]
GAMING_QUERIES = [
    'video games PlayStation Xbox Nintendo',
    'PC gaming Steam game release',
    'video game studio developer publisher release',
    'Nintendo Switch PlayStation Xbox gaming news',
    'esports video game gaming',
]
US_QUERIES = [
    'United States national news Americans nationwide',
    'US public health education national news',
    'US consumers housing jobs national news',
    'US immigration civil rights national news',
]

TECH_TRUSTED = (
    'reuters','associated press','ap news','the verge','ars technica','techcrunch','wired',
    "tom's hardware",'engadget','pcmag','mit technology review','cnbc','axios','cnet','zdnet',
    'bbc','the guardian','new york times','washington post','bloomberg','fortune',
)
GAMING_TRUSTED = (
    'ign','gamespot','pc gamer','polygon','nintendo life','eurogamer','kotaku','game informer',
    'the verge','ars technica','windows central',"tom's hardware",'cnet','engadget',
)
US_TRUSTED = (
    'reuters','associated press','ap news','nbc news','cbs news','abc news','cnn','usa today',
    'new york times','washington post','time','bbc','npr','axios','the hill','politico',
)

TECH_STRONG_TERMS = (
    'artificial intelligence',' ai ','ai model','machine learning','large language model','llm',
    'openai','anthropic','cybersecurity','cyberattack','ransomware','data breach','malware',
    'semiconductor','chip','gpu','cpu','processor','quantum computing','robotics','humanoid robot',
    'operating system','software','cloud computing','data center','database','browser','chrome',
    'browser extension','iphone','ipad','android','macbook','windows','linux','smartphone','laptop',
    'computer','pc display','monitor','hardware','wearable','smart glasses','virtual reality',
    'mixed reality','spatial computing','satellite internet','app store','mobile app','tech industry',
)
TECH_COMPANIES = (
    'apple','google','microsoft','nvidia','amd','intel','meta','amazon','qualcomm','samsung','tesla',
    'linkedin','github','adobe','oracle','ibm','salesforce','spotify','tiktok','snap','x corp',
)
TECH_CONTEXT_TERMS = (
    'device','platform','app','software','hardware','chip','processor','model','browser','extension',
    'privacy','security','data','cloud','compute','computer','phone','smartphone','laptop','display',
    'network','internet','digital','algorithm','developer','coding','programming','startup technology',
)
TECH_IMPACT = (
    'launch','unveil','release','announces','announced','breakthrough','breach','hack','ransomware',
    'outage','ban','lawsuit','acquisition','merger','layoffs','regulation','security flaw','vulnerability',
    'new model','new chip','new gpu','new cpu','antitrust','recall','shutdown','partnership with openai',
)
TECH_LOW_VALUE = (
    'review:',' review','how to','best ','deal','sale','guide','roundup','explainer','hands-on',
    'incubator','chamber of commerce','opens office','local startup','joins accelerator','hiring event',
)
TECH_MARKET_ONLY = (
    'shares rise','shares fall','shares plunge','stocks rise','stocks fall','stocks plunge','market rally',
    'market selloff','wall street','dow ','s&p 500','nasdaq',
)
TECH_SUPPORT_TITLE_PATTERNS = (
    re.compile(r'^\s*(?:question|help|support|troubleshooting)\s*[-–—:]', re.I),
    re.compile(r'^\s*(?:how do i|how to fix|why does my|is my)\b', re.I),
)

GAMING_STRONG = (
    'video game','playstation','xbox','nintendo','switch 2','nintendo switch','steam','pc gaming',
    'game pass','esports','dlc','game studio','game developer','game publisher','epic games',
    'unreal engine','release date','gameplay','gaming console','handheld gaming','ps5','xbox series',
)
GAMING_HARDWARE = (
    'gaming monitor','gaming laptop','gaming pc','graphics card','gpu','controller','gaming handheld',
    'rog ally','steam deck','gaming headset','gaming keyboard','gaming mouse',
)
GAMING_EXCLUDE = (
    'casino','gambling','sportsbook','lottery','slot machine','tabletop','board game','miniatures',
    'warhammer','card packs','trading card','hobby store','gaming store','poker','bingo',
)
GAMING_LOW_VALUE = (
    'review:',' review','deal','sale','best ','guide','roundup','coupon','promo code','giveaway','sweepstakes',
)

FEDERAL_ROUTE = re.compile(
    r'\b(congress|u\.?s\.? senate|senate committee|house committee|house of representatives|house speaker|'
    r'supreme court|scotus|department of justice|doj|fbi|dhs|irs|epa|treasury department|federal court|'
    r'federal judge|federal agency|census bureau|federal government)\b', re.I)
PRESIDENTIAL_ROUTE = re.compile(
    r"\b(president trump|donald trump|trump(?:'s|’s)?|trump administration|white house|executive order|oval office|press secretary)\b", re.I)
FOREIGN_US_FALSE_POSITIVE = re.compile(
    r'\b(london|paris|berlin|rome|madrid|moscow|kyiv|beijing|tokyo|seoul|gaza|israel|ukraine|russia|china|'
    r'uk|u\.k\.|united kingdom|britain|france|germany|italy|spain|india|pakistan|australia|canada|mexico)\b', re.I)
US_NATIONAL = re.compile(
    r'\b(united states|u\.?s\.?|americans?|nationwide|across the country|across the u\.?s\.?|multiple states|'
    r'census|immigration|civil rights|abortion|gun laws?|health insurance|housing market|consumers?|'
    r'social security|medicare|medicaid|public schools?|nationally|states? face|states? are)\b', re.I)
LOW_VALUE_GENERAL = re.compile(
    r'\b(horoscope|winning numbers|lottery results?|things to do|letter to the editor|letters to the editor|'
    r'food service inspections?|restaurant inspections?|high school football|prep football)\b', re.I)

NON_ARTICLE_PREFIXES = (
    'tag:', 'topic:', 'category:', 'author:', 'authors:', 'archive:', 'archives:', 'page:',
    'search results', 'search:', 'podcasts:', 'videos:', 'gallery:', 'galleries:'
)


def clean(value):
    value = html.unescape(value or '')
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def text(item, tag):
    return clean(item.findtext(tag))


def set_text(item, tag, value):
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = value


def parse_date(value):
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def age_hours(item):
    dt = parse_date(text(item, 'pubDate'))
    if dt.year < 1900:
        return 9999
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)


def source_family(source):
    return re.sub(r'[^a-z0-9]+', ' ', (source or '').lower()).strip()


def canonical_title(item):
    title = text(item, 'title')
    source = text(item, 'source')
    if source:
        title = re.sub(rf'\s*[-–—|:]\s*{re.escape(source)}\s*$', '', title, flags=re.I)
    return re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()


def article_like_title(title):
    value = clean(title)
    lower = value.lower().strip()
    if not value or any(lower.startswith(prefix) for prefix in NON_ARTICLE_PREFIXES):
        return False
    if re.match(r'^(?:tag|topic|category|author|archive|search)\s*[-–—:|]', lower):
        return False
    return len(re.findall(r'[A-Za-z0-9][A-Za-z0-9+.-]*', value)) >= 4


def token_set(item):
    stop = {'the','a','an','and','or','to','of','in','on','for','with','at','by','from','is','are','was','were','new','news','says'}
    return {w for w in canonical_title(item).split() if len(w) > 2 and w not in stop}


def near_same(a, b):
    ca, cb = canonical_title(a), canonical_title(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    ta, tb = token_set(a), token_set(b)
    if ta and tb:
        smaller = min(len(ta), len(tb))
        if smaller >= 4 and len(ta & tb) / smaller >= 0.70:
            return True
    return min(len(ca), len(cb)) >= 35 and difflib.SequenceMatcher(None, ca, cb).ratio() >= 0.86


def source_is(source, trusted):
    s = source_family(source)
    return any(token in s for token in trusted)


def tech_relevance_decision(item):
    title = text(item, 'title')
    desc = text(item, 'description')
    if not article_like_title(title) or any(p.search(title) for p in TECH_SUPPORT_TITLE_PATTERNS):
        return 'drop'
    raw = f' {title} {desc} '.lower()
    if re.search(r'\b(fcc|federal communications commission|ftc|federal trade commission|congress|senate|house committee|supreme court|federal court|white house|justice department|department of justice|doj|federal government|federal regulator)\b', raw):
        return 'federal'
    if any(term in raw for term in ('climate change','global warming','global temperature','hottest month','temperature record','el niño','el nino','un climate','climate summit','world meteorological organization')):
        return 'world'
    if any(term in raw for term in ('broadway','hbo max','tv show','television show','box office','season premiere')) and not any(term in raw for term in TECH_STRONG_TERMS):
        return 'drop'
    strong = any(term in raw for term in TECH_STRONG_TERMS)
    company_context = any(company in raw for company in TECH_COMPANIES) and any(term in raw for term in TECH_CONTEXT_TERMS)
    return 'technology' if strong or company_context else 'drop'


def gaming_allowed(item):
    title = text(item, 'title')
    desc = text(item, 'description')
    if not article_like_title(title):
        return False
    raw = f' {title} {desc} '.lower()
    if any(term in raw for term in GAMING_EXCLUDE):
        return False
    strong = any(term in raw for term in GAMING_STRONG)
    hardware = any(term in raw for term in GAMING_HARDWARE)
    trusted = source_is(text(item, 'source'), GAMING_TRUSTED)
    return strong or hardware or trusted


def us_route(item):
    title = text(item, 'title')
    desc = text(item, 'description')
    raw = f'{title} {desc}'
    if LOW_VALUE_GENERAL.search(raw):
        return 'drop'
    if PRESIDENTIAL_ROUTE.search(title):
        return 'presidential'
    if FEDERAL_ROUTE.search(title):
        return 'federal'
    if re.search(r'\b(?:u\.?s\.?|american) embassy\b', title, re.I) and FOREIGN_US_FALSE_POSITIVE.search(raw):
        return 'world'
    if FOREIGN_US_FALSE_POSITIVE.search(title) and not US_NATIONAL.search(title):
        return 'world'
    return 'us' if US_NATIONAL.search(raw) else 'drop'


def feed_url(query, days=2):
    q = urllib.parse.quote(f'{query} when:{days}d')
    return f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'


def fetch_google(queries, category, days=2):
    found = []
    seen = set()
    for query in queries:
        try:
            req = urllib.request.Request(feed_url(query, days), headers={'User-Agent':'Mozilla/5.0 UnderreportedNews/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                root = ET.fromstring(response.read())
        except Exception as exc:
            print(f'Google News discovery skipped for {query!r}: {exc}')
            continue
        for src in root.findall('.//item'):
            title = clean(src.findtext('title'))
            link = clean(src.findtext('link'))
            desc = clean(src.findtext('description'))
            pub = clean(src.findtext('pubDate'))
            source_el = src.find('source')
            source = clean(source_el.text if source_el is not None else '')
            if not title or not link or not article_like_title(title):
                continue
            key = re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            item = ET.Element('item')
            ET.SubElement(item, 'title').text = title
            ET.SubElement(item, 'link').text = link
            ET.SubElement(item, 'description').text = desc
            ET.SubElement(item, 'pubDate').text = pub
            ET.SubElement(item, 'source').text = source
            ET.SubElement(item, 'category').text = category
            ET.SubElement(item, 'guid', {'isPermaLink':'false'}).text = hashlib.sha1(link.encode()).hexdigest()
            found.append(item)
    return found


def cluster_items(items):
    clusters = []
    for item in sorted(items, key=lambda i: parse_date(text(i, 'pubDate')), reverse=True):
        placed = False
        for cluster in clusters:
            if near_same(item, cluster[0]):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters


def add_rank_fields(item, prefix, score, coverage):
    set_text(item, prefix + 'Score', str(int(score)))
    set_text(item, prefix + 'Coverage', str(int(coverage)))


def tech_cluster_score(cluster):
    lead = max(cluster, key=lambda i: parse_date(text(i, 'pubDate')))
    raw = f" {text(lead,'title')} {text(lead,'description')} ".lower()
    coverage = len({source_family(text(i,'source')) for i in cluster if text(i,'source')}) or 1
    score = coverage * 110
    score += max(0, 72 - age_hours(lead))
    score += 45 * sum(1 for term in TECH_IMPACT if term in raw)
    if source_is(text(lead,'source'), TECH_TRUSTED):
        score += 35
    if any(term in raw for term in TECH_LOW_VALUE):
        score -= 110
    if any(term in raw for term in TECH_MARKET_ONLY):
        score -= 70
    if re.search(r'\b(local|city|county|incubator|accelerator)\b', raw) and coverage < 2:
        score -= 180
    return score, coverage, lead


def gaming_cluster_score(cluster):
    lead = max(cluster, key=lambda i: parse_date(text(i, 'pubDate')))
    raw = f" {text(lead,'title')} {text(lead,'description')} ".lower()
    coverage = len({source_family(text(i,'source')) for i in cluster if text(i,'source')}) or 1
    score = coverage * 110 + max(0, 72 - age_hours(lead))
    score += 40 * sum(1 for term in GAMING_STRONG if term in raw)
    if source_is(text(lead,'source'), GAMING_TRUSTED):
        score += 35
    if any(term in raw for term in GAMING_LOW_VALUE):
        score -= 80
    if any(term in raw for term in GAMING_HARDWARE) and not any(term in raw for term in ('playstation','xbox','nintendo','steam','game pass','video game')):
        score -= 25
    return score, coverage, lead


def rank_technology(existing):
    pool = []
    rerouted = []
    for item in existing:
        decision = tech_relevance_decision(item)
        if decision == 'technology':
            pool.append(item)
        elif decision in ('federal','world'):
            set_text(item, 'category', decision)
            rerouted.append(item)
    for item in fetch_google(TECH_QUERIES, 'technology', 7):
        if tech_relevance_decision(item) == 'technology':
            pool.append(item)
    ranked = []
    for cluster in cluster_items(pool):
        score, coverage, lead = tech_cluster_score(cluster)
        if score < 40:
            continue
        add_rank_fields(lead, 'technology', score, coverage)
        ranked.append((score, parse_date(text(lead,'pubDate')), lead))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[2] for row in ranked[:MAX_TECH]], rerouted


def rank_gaming(existing):
    pool = [item for item in existing if gaming_allowed(item)]
    for item in fetch_google(GAMING_QUERIES, 'gaming', 7):
        if gaming_allowed(item):
            pool.append(item)
    ranked = []
    for cluster in cluster_items(pool):
        score, coverage, lead = gaming_cluster_score(cluster)
        if score < 45:
            continue
        add_rank_fields(lead, 'gaming', score, coverage)
        ranked.append((score, parse_date(text(lead,'pubDate')), lead))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[2] for row in ranked[:MAX_GAMING]]


def refine_us(existing):
    kept = []
    rerouted = []
    for item in existing:
        route = us_route(item)
        if route == 'us':
            kept.append(item)
        elif route in ('world','federal','presidential'):
            set_text(item, 'category', route)
            rerouted.append(item)
    supplemental = fetch_google(US_QUERIES, 'us', 7)
    for item in supplemental:
        if source_is(text(item,'source'), US_TRUSTED) and us_route(item) == 'us':
            kept.append(item)
    clusters = cluster_items(kept)
    ranked = []
    for cluster in clusters:
        lead = max(cluster, key=lambda i: parse_date(text(i,'pubDate')))
        coverage = len({source_family(text(i,'source')) for i in cluster if text(i,'source')}) or 1
        score = coverage * 90 + max(0, 60 - age_hours(lead))
        if source_is(text(lead,'source'), US_TRUSTED):
            score += 25
        add_rank_fields(lead, 'us', score, coverage)
        ranked.append((score, parse_date(text(lead,'pubDate')), lead))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[2] for row in ranked[:MAX_US]], rerouted


def replace_categories(channel, categories, replacement):
    items = list(channel.findall('item'))
    first = min([idx for idx,item in enumerate(items) if text(item,'category') in categories] or [len(items)])
    for item in items:
        if text(item,'category') in categories:
            channel.remove(item)
    current = list(channel.findall('item'))
    first = min(first, len(current))
    for offset, item in enumerate(replacement):
        channel.insert(first + offset, item)


def main():
    if not NEWS.exists():
        raise SystemExit('News feed not found')
    tree = ET.parse(NEWS)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')
    items = list(channel.findall('item'))
    tech_existing = [i for i in items if text(i,'category') == 'technology']
    gaming_existing = [i for i in items if text(i,'category') == 'gaming']
    us_existing = [i for i in items if text(i,'category') == 'us']

    tech, tech_routes = rank_technology(tech_existing)
    gaming = rank_gaming(gaming_existing)
    us, us_routes = refine_us(us_existing)
    routed = tech_routes + us_routes

    replace_categories(channel, {'technology','gaming','us'}, tech + gaming + us + routed)
    tree.write(NEWS, encoding='utf-8', xml_declaration=True)

    counts = {}
    for item in channel.findall('item'):
        cat = text(item,'category')
        counts[cat] = counts.get(cat, 0) + 1
    print(
        'Topic refinement:',
        f"technology {len(tech_existing)}->{len(tech)};",
        f"gaming {len(gaming_existing)}->{len(gaming)};",
        f"us {len(us_existing)}->{len(us)};",
        f"rerouted={len(routed)};",
        'final category counts',
        {k: counts.get(k,0) for k in ('technology','gaming','us','world','federal','presidential')},
    )


if __name__ == '__main__':
    main()