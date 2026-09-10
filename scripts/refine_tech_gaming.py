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
MAX_TECH = 30
MAX_GAMING = 30

TECH_DISCOVERY_QUERIES = [
    'upcoming technology launch new device next generation roadmap',
    'AI model launch robotics quantum computing battery technology',
    'Apple Google Microsoft Nvidia AMD Intel upcoming product launch',
    'AR glasses VR headset smartphone laptop chip launch roadmap',
]

TECH_TRUSTED = (
    'the verge','ars technica','techcrunch','wired','tom\'s hardware','engadget','pcmag','pc magazine',
    'mit technology review','reuters','associated press','ap news','cnbc','axios','forbes','cnet','zdnet',
)

GAMING_ANCHORS = (
    'game','gaming','playstation','xbox','nintendo','switch','steam','pc gaming','console','game pass',
    'developer','studio','publisher','release date','dlc','esports','controller','handheld','gpu',
    'kojima','metal gear','physint','zelda','mario','pokemon','unreal engine','epic games',
)

GAMING_JUNK = (
    'giveaway','sweepstakes','contest','win a ','free giveaway','deal of the day','coupon','promo code',
    'best deals','sale ends','buy now','gift guide',
)

TECH_UPCOMING = (
    'upcoming','launch','launches','launching','release date','coming soon','coming in','next-gen',
    'next generation','roadmap','unveil','unveiled','prototype','preview','beta','debut','announced',
    'announces','new chip','new gpu','new cpu','new device','new model','2027',
)

TECH_EMERGING = (
    'quantum','robotics','robot','humanoid','solid-state battery','battery breakthrough','fusion',
    'ar glasses','smart glasses','mixed reality','spatial computing','neural','photonic','ai model',
    'gpu','cpu','semiconductor','chip','wearable','foldable','satellite internet',
)

LOW_VALUE = ('opinion','review','how to','best ','deal','sale','guide','roundup','explainer')


def clean(value):
    value = html.unescape(value or '')
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def text(item, tag):
    return clean(item.findtext(tag))


def parse_date(value):
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def source_family(source):
    s = re.sub(r'[^a-z0-9]+', ' ', (source or '').lower()).strip()
    if 'ign' in s:
        return 'ign'
    if 'gamespot' in s:
        return 'gamespot'
    if 'pc gamer' in s:
        return 'pc gamer'
    if 'nintendo life' in s:
        return 'nintendo life'
    if 'polygon' in s:
        return 'polygon'
    return s


def canonical_title(item):
    title = text(item, 'title')
    source = text(item, 'source')
    if source:
        title = re.sub(rf'\s*[-–—|:]\s*{re.escape(source)}\s*$', '', title, flags=re.I)
    title = re.sub(r'\s*[-–—|:]\s*IGN(?:\s+Nordic)?\s*$', '', title, flags=re.I)
    title = re.sub(r'\s*[-–—|:]\s*(?:GameSpot|PC Gamer|Polygon|Nintendo Life)\s*$', '', title, flags=re.I)
    return re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()


def near_same(a, b):
    ca, cb = canonical_title(a), canonical_title(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    ta, tb = set(ca.split()), set(cb.split())
    if ta and tb:
        smaller = min(len(ta), len(tb))
        if smaller >= 4 and len(ta & tb) / smaller >= 0.82:
            return True
    return min(len(ca), len(cb)) >= 35 and difflib.SequenceMatcher(None, ca, cb).ratio() >= 0.90


def gaming_allowed(item):
    title = text(item, 'title')
    desc = text(item, 'description')
    raw = f'{title} {desc}'.lower()
    if any(term in raw for term in GAMING_JUNK):
        return False
    base = canonical_title(item)
    meaningful = [w for w in base.split() if len(w) > 2]
    if len(meaningful) <= 2:
        return False
    movie_tv = any(term in raw for term in (' movie','film ',' tv ','television','box office','season premiere','actor '))
    anchored = any(term in raw for term in GAMING_ANCHORS)
    if movie_tv and not anchored:
        return False
    return anchored


def refine_gaming(items):
    candidates = [i for i in items if gaming_allowed(i)]
    candidates.sort(key=lambda i: parse_date(text(i, 'pubDate')), reverse=True)
    kept = []
    source_counts = {}
    for item in candidates:
        family = source_family(text(item, 'source'))
        if source_counts.get(family, 0) >= 5:
            continue
        if any(near_same(item, prior) for prior in kept):
            continue
        kept.append(item)
        source_counts[family] = source_counts.get(family, 0) + 1
        if len(kept) >= MAX_GAMING:
            break
    return kept


def tech_score(item):
    raw = f"{text(item,'title')} {text(item,'description')}".lower()
    score = 0
    score += 55 * sum(1 for term in TECH_UPCOMING if term in raw)
    score += 30 * sum(1 for term in TECH_EMERGING if term in raw)
    score -= 30 * sum(1 for term in LOW_VALUE if term in raw)
    dt = parse_date(text(item, 'pubDate'))
    if dt.year > 1900:
        hours = max(0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
        score += max(0, 48 - hours)
    return score


def feed_url(query):
    q = urllib.parse.quote(f'{query} when:2d')
    return f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'


def source_trusted(source):
    s = (source or '').lower()
    return any(token in s for token in TECH_TRUSTED)


def fetch_upcoming_tech():
    found = []
    seen = set()
    for query in TECH_DISCOVERY_QUERIES:
        try:
            req = urllib.request.Request(feed_url(query), headers={'User-Agent':'Mozilla/5.0 TechDiscovery/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                root = ET.fromstring(response.read())
        except Exception:
            continue
        for src_item in root.findall('.//item'):
            title = clean(src_item.findtext('title'))
            link = clean(src_item.findtext('link'))
            desc = clean(src_item.findtext('description'))
            pub = clean(src_item.findtext('pubDate'))
            source_el = src_item.find('source')
            source = clean(source_el.text if source_el is not None else '')
            if not title or not link or not source_trusted(source):
                continue
            key = re.sub(r'[^a-z0-9]+',' ',title.lower()).strip()
            if key in seen:
                continue
            raw = f'{title} {desc}'.lower()
            if not any(term in raw for term in TECH_UPCOMING + TECH_EMERGING):
                continue
            seen.add(key)
            item = ET.Element('item')
            ET.SubElement(item,'title').text = title
            ET.SubElement(item,'link').text = link
            ET.SubElement(item,'description').text = desc
            ET.SubElement(item,'pubDate').text = pub
            ET.SubElement(item,'source').text = source
            ET.SubElement(item,'category').text = 'technology'
            ET.SubElement(item,'region').text = ''
            ET.SubElement(item,'whyMatters').text = 'Why it matters: This could shape upcoming devices, platforms, chips, AI systems, or the direction of consumer and enterprise technology.'
            ET.SubElement(item,'guid', {'isPermaLink':'false'}).text = hashlib.sha1(link.encode()).hexdigest()
            found.append(item)
    return found


def refine_technology(existing):
    combined = list(existing) + fetch_upcoming_tech()
    unique = []
    seen_links = set()
    seen_titles = set()
    for item in combined:
        link = text(item,'link')
        title_key = canonical_title(item)
        if not link or link in seen_links or not title_key or title_key in seen_titles:
            continue
        seen_links.add(link); seen_titles.add(title_key); unique.append(item)
    unique.sort(key=lambda i: (tech_score(i), parse_date(text(i,'pubDate'))), reverse=True)
    return unique[:MAX_TECH]


def replace_category(channel, category, replacement):
    items = channel.findall('item')
    first_index = next((idx for idx,item in enumerate(items) if text(item,'category') == category), len(items))
    for item in list(items):
        if text(item,'category') == category:
            channel.remove(item)
    current = list(channel.findall('item'))
    insert_at = min(first_index, len(current))
    for offset, item in enumerate(replacement):
        channel.insert(insert_at + offset, item)


def main():
    if not NEWS.exists():
        raise SystemExit('News feed not found')
    tree = ET.parse(NEWS)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')
    items = channel.findall('item')
    gaming = [i for i in items if text(i,'category') == 'gaming']
    tech = [i for i in items if text(i,'category') == 'technology']
    new_gaming = refine_gaming(gaming)
    new_tech = refine_technology(tech)
    replace_category(channel, 'technology', new_tech)
    replace_category(channel, 'gaming', new_gaming)
    tree.write(NEWS, encoding='utf-8', xml_declaration=True)
    print(f'Gaming quality: {len(gaming)} -> {len(new_gaming)} relevant, deduplicated stories.')
    print(f'Technology quality: {len(tech)} existing -> {len(new_tech)} stories, with upcoming/emerging tech promoted.')

if __name__ == '__main__':
    main()
