from pathlib import Path
from datetime import datetime, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NEWS = Path('News')
CONGRESS = 119
NM_SESSION_CODE = '23RS'  # nmlegis internal code for the 2026 Regular Session
MAX_FEDERAL = 18
MAX_NM = 14
CONGRESS_API_KEY = (os.environ.get('CONGRESS_API_KEY') or '').strip()


def request_text(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 OfficialLegislationTracker/3.0'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='replace')


def request_json(url):
    return json.loads(request_text(url))


def clean(value):
    value = html.unescape(value or '')
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def iso_to_rfc(value):
    if value:
        for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%SZ'):
            try:
                return format_datetime(datetime.strptime(value[:len(fmt.replace('%',''))], fmt).replace(tzinfo=timezone.utc))
            except Exception:
                pass
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return format_datetime(dt.astimezone(timezone.utc))
        except Exception:
            pass
    return format_datetime(datetime.now(timezone.utc))


def status_from_action(action):
    t = (action or '').lower()
    if any(x in t for x in ('became public law', 'signed by president', 'signed by governor', 'sgnd by gov', 'chaptered')):
        return 'Signed / enacted'
    if 'veto' in t:
        return 'Vetoed'
    if any(x in t for x in ('passed house and senate', 'passed both', 'passed/s', 'passed/h')):
        return 'Passed chamber / legislature'
    if any(x in t for x in ('reported by', 'do pass', 'dp', 'ordered to be reported')):
        return 'Advanced from committee'
    if any(x in t for x in ('introduced', 'referred', 'sent to')):
        return 'Introduced / referred'
    return 'Active / current record'


def next_step_for(status):
    return {
        'Signed / enacted': 'Implementation, effective dates, agency guidance, and any court challenges.',
        'Vetoed': 'Watch for an override attempt or replacement legislation.',
        'Passed chamber / legislature': 'Watch the remaining chamber, executive action, reconciliation, or implementation.',
        'Advanced from committee': 'Possible floor consideration, amendments, or additional committee action.',
        'Introduced / referred': 'Committee hearings, markup, amendments, or floor consideration.',
    }.get(status, 'Watch the next formal legislative action.')


def affected_from_text(text):
    t = (text or '').lower()
    groups = [
        ('Patients, providers, and health programs', ('health', 'medicaid', 'medicare', 'hospital', 'medical', 'drug')),
        ('Workers and employers', ('worker', 'labor', 'wage', 'union', 'employment', 'apprentice')),
        ('Students, families, and schools', ('school', 'student', 'education', 'college', 'teacher', 'literacy')),
        ('Veterans, service members, and military families', ('veteran', 'military', 'armed forces', 'defense')),
        ('Taxpayers, households, and businesses', ('tax', 'budget', 'appropriation', 'spending', 'credit', 'bond')),
        ('Immigrants and immigration agencies', ('immigration', 'immigrant', 'border', 'asylum', 'visa')),
        ('Tribal governments and Indigenous communities', ('tribal', 'native american', 'indian', 'navajo')),
        ('Consumers and regulated businesses', ('consumer', 'insurance', 'bank', 'financial', 'regulation', 'licensure')),
        ('Residents, utilities, and water users', ('water', 'utility', 'electric', 'energy', 'environment', 'highway')),
        ('People affected by criminal-justice policy', ('criminal', 'parole', 'juvenile', 'law enforcement', 'burglary')),
    ]
    for label, terms in groups:
        if any(term in t for term in terms):
            return label
    return 'People, agencies, businesses, or programs covered by the measure'


def significant(title, action=''):
    text = f'{title} {action}'.lower()
    low = ('commemorat', 'post office', 'naming', 'designat', 'coin', 'medal', 'recogniz', 'memorial')
    if any(x in text for x in low):
        return False
    important = (
        'appropriation', 'budget', 'tax', 'health', 'medicaid', 'medicare', 'housing', 'immigration', 'border',
        'military', 'war powers', 'voting', 'election', 'privacy', 'surveillance', 'education', 'student', 'labor',
        'wage', 'energy', 'environment', 'water', 'tribal', 'native american', 'social security', 'benefit',
        'artificial intelligence', 'cyber', 'consumer', 'bank', 'insurance', 'drug', 'abortion', 'firearm',
        'transportation', 'highway', 'public safety', 'criminal', 'juvenile', 'parole', 'child', 'family',
        'appropriations', 'fund', 'bond', 'licensure', 'affordability', 'public education', 'regulation'
    )
    # Bills with meaningful formal action may be useful even when title keywords are terse.
    meaningful_action = any(x in text for x in ('signed', 'chapter', 'passed', 'public law', 'veto', 'reported by committee'))
    return meaningful_action or any(x in text for x in important)


TYPE_SLUG = {
    'HR': 'house-bill', 'S': 'senate-bill', 'HJRES': 'house-joint-resolution', 'SJRES': 'senate-joint-resolution',
    'HCONRES': 'house-concurrent-resolution', 'SCONRES': 'senate-concurrent-resolution',
    'HRES': 'house-resolution', 'SRES': 'senate-resolution'
}
TYPE_LABEL = {'HR':'H.R.', 'S':'S.', 'HJRES':'H.J.Res.', 'SJRES':'S.J.Res.', 'HCONRES':'H.Con.Res.', 'SCONRES':'S.Con.Res.', 'HRES':'H.Res.', 'SRES':'S.Res.'}


def congress_url(btype, number):
    return f'https://www.congress.gov/bill/{CONGRESS}th-congress/{TYPE_SLUG.get(btype, "house-bill")}/{number}'


def parse_congress_id(text):
    t = (text or '').upper().replace('.', '')
    patterns = [
        ('HJRES', r'\bH\s*J\s*RES\s*(\d+)\b'), ('SJRES', r'\bS\s*J\s*RES\s*(\d+)\b'),
        ('HCONRES', r'\bH\s*CON\s*RES\s*(\d+)\b'), ('SCONRES', r'\bS\s*CON\s*RES\s*(\d+)\b'),
        ('HRES', r'\bH\s*RES\s*(\d+)\b'), ('SRES', r'\bS\s*RES\s*(\d+)\b'),
        ('HR', r'\bH\s*R\s*(\d+)\b'), ('S', r'\bS\s+(\d+)\b'),
    ]
    for btype, pat in patterns:
        m = re.search(pat, t)
        if m:
            return btype, m.group(1)
    return None


def google_feed(query):
    q = urllib.parse.quote(query)
    return f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'


def congress_candidates_from_public_search():
    queries = [
        'site:congress.gov/bill/119th-congress Congress.gov bill',
        'site:congress.gov/bill/119th-congress health tax education immigration bill Congress.gov',
        'site:congress.gov/bill/119th-congress defense privacy technology budget Congress.gov',
    ]
    out, seen = [], set()
    for query in queries:
        try:
            root = ET.fromstring(request_text(google_feed(query)))
        except Exception:
            continue
        for item in root.findall('.//item'):
            title = clean(item.findtext('title'))
            ident = parse_congress_id(title)
            if not ident or ident in seen:
                continue
            seen.add(ident)
            out.append((ident[0], ident[1], title))
            if len(out) >= 60:
                return out
    return out


def parse_congress_page(btype, number, fallback_title):
    url = congress_url(btype, number)
    try:
        raw = request_text(url)
    except Exception:
        raw = ''
    text = clean(raw)
    title = ''
    sponsor = ''
    action = ''
    summary = ''
    if text:
        # Congress.gov pages expose these labels in the rendered HTML/text.
        m = re.search(r'(?:Official Title as Introduced|Short Titles?|Title)\s*:?\s*(.{15,260}?)(?:Sponsor:|Committees:|Latest Action:|Tracker:|All Information)', text, re.I)
        if m: title = clean(m.group(1))
        m = re.search(r'Sponsor:\s*(.{3,120}?)(?:\[|Committees:|Latest Action:)', text, re.I)
        if m: sponsor = clean(m.group(1))
        m = re.search(r'Latest Action:\s*(.{15,500}?)(?:All Actions|Tracker:|Give Feedback|$)', text, re.I)
        if m: action = clean(m.group(1))
        m = re.search(r'(?:Summary|Bill Summary)\s*(.{60,1200}?)(?:Subject|Latest Summary|Text|Cosponsors|Committees)', text, re.I)
        if m: summary = clean(m.group(1))
    if not title:
        # Remove trailing source label and bill number from discovery title.
        title = re.sub(r'\s*[-–—]\s*Congress\.gov\s*$', '', fallback_title, flags=re.I)
        title = re.sub(r'^\s*(?:H\.?R\.?|S\.?|H\.?J\.?Res\.?|S\.?J\.?Res\.?)\s*\d+\s*[-–—:]?\s*', '', title, flags=re.I).strip()
    if not action:
        action = 'See Congress.gov for the latest official action.'
    if not significant(title, action):
        return None
    status = status_from_action(action)
    return {
        'title': f'{TYPE_LABEL.get(btype,btype)} {number} — {title}', 'link': url, 'source': 'Congress.gov',
        'pubDate': format_datetime(datetime.now(timezone.utc)), 'jurisdiction': 'Federal', 'status': status,
        'whatItDoes': summary or title, 'whoAffected': affected_from_text(f'{title} {summary}'),
        'effectiveDate': 'See enacted text if signed into law', 'nextStep': next_step_for(status), 'officialSource': url,
        'billNumber': f'{TYPE_LABEL.get(btype,btype)} {number}', 'latestAction': action, 'sponsor': sponsor,
    }


def fetch_federal_api():
    if not CONGRESS_API_KEY or CONGRESS_API_KEY.upper() == 'DEMO_KEY':
        return []
    base = f'https://api.congress.gov/v3/bill/{CONGRESS}?format=json&limit=100&api_key={urllib.parse.quote(CONGRESS_API_KEY)}'
    data = request_json(base)
    rows = []
    for bill in data.get('bills', []):
        btype = str(bill.get('type') or '').upper(); number = str(bill.get('number') or '')
        title = clean(bill.get('title')); latest = bill.get('latestAction') or {}; action = clean(latest.get('text'))
        if not btype or not number or not significant(title, action):
            continue
        url = congress_url(btype, number); status = status_from_action(action)
        rows.append({'title':f'{TYPE_LABEL.get(btype,btype)} {number} — {title}','link':url,'source':'Congress.gov',
            'pubDate':iso_to_rfc(latest.get('actionDate') or bill.get('updateDate') or ''),'jurisdiction':'Federal','status':status,
            'whatItDoes':title,'whoAffected':affected_from_text(title),'effectiveDate':'See enacted text if signed into law',
            'nextStep':next_step_for(status),'officialSource':url,'billNumber':f'{TYPE_LABEL.get(btype,btype)} {number}',
            'latestAction':action or 'See Congress.gov for the latest official action.','sponsor':''})
        if len(rows) >= MAX_FEDERAL: break
    return rows


def fetch_federal():
    try:
        rows = fetch_federal_api()
    except Exception:
        rows = []
    if len(rows) >= 10:
        return rows[:MAX_FEDERAL]
    rows, seen = [], set()
    for btype, number, discovery_title in congress_candidates_from_public_search():
        if (btype, number) in seen: continue
        seen.add((btype, number))
        row = parse_congress_page(btype, number, discovery_title)
        if row: rows.append(row)
        if len(rows) >= MAX_FEDERAL: break
    return rows


class NMListParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.in_tr=False; self.in_cell=False; self.cells=[]; self.cell=[]; self.rows=[]; self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='tr': self.in_tr=True; self.cells=[]; self.hrefs=[]
        elif self.in_tr and tag in ('td','th'): self.in_cell=True; self.cell=[]
        elif self.in_tr and tag=='a':
            href=attrs.get('href','')
            if href: self.hrefs.append(href)
    def handle_data(self, data):
        if self.in_tr and self.in_cell:
            v=clean(data)
            if v: self.cell.append(v)
    def handle_endtag(self, tag):
        if self.in_tr and tag in ('td','th'):
            self.in_cell=False; self.cells.append(' '.join(self.cell).strip())
        elif tag=='tr' and self.in_tr:
            self.in_tr=False
            if self.cells: self.rows.append((self.cells[:], self.hrefs[:]))


def nm_official_url(bill_id):
    m=re.match(r'\*?\s*(HB|SB)\s*(\d+)',bill_id,re.I)
    if not m: return ''
    chamber='H' if m.group(1).upper()=='HB' else 'S'
    return f'https://www.nmlegis.gov/Legislation/Legislation?Chamber={chamber}&LegNo={m.group(2)}&LegType=B&year=26'


def fetch_nm():
    url=f'https://www.nmlegis.gov/Legislation/Legislation_List?Session={NM_SESSION_CODE}'
    raw=request_text(url)
    parser=NMListParser(); parser.feed(raw)
    candidates=[]
    for cells, hrefs in parser.rows:
        if len(cells)<4: continue
        bill_id=clean(cells[0]).replace('*','').strip()
        if not re.fullmatch(r'(?:HB|SB)\s*\d+',bill_id,re.I): continue
        title=clean(cells[1]); sponsor=clean(cells[2]); action=clean(cells[3]); session=clean(cells[4]) if len(cells)>4 else ''
        if session and '2026 Regular' not in session: continue
        if any(x in action.lower() for x in ('substituted', 'died', 'api.')) and 'sgnd by gov' not in action.lower(): continue
        if not significant(title, action): continue
        official=nm_official_url(bill_id)
        status=status_from_action(action)
        # rank enacted/passed items above merely introduced items
        rank=(3 if 'Signed / enacted'==status else 2 if 'Passed' in status else 1, len(action))
        candidates.append((rank, {'title':f'{bill_id.upper()} — {title.title() if title.isupper() else title}', 'link':official,
            'source':'New Mexico Legislature','pubDate':format_datetime(datetime.now(timezone.utc)),'jurisdiction':'New Mexico',
            'status':status,'whatItDoes':title.title() if title.isupper() else title,'whoAffected':affected_from_text(title),
            'effectiveDate':'See official bill text / chaptered law','nextStep':next_step_for(status),'officialSource':official,
            'billNumber':bill_id.upper(),'latestAction':action or status,'sponsor':sponsor}))
    candidates.sort(key=lambda x:x[0], reverse=True)
    return [row for _,row in candidates[:MAX_NM]]


def set_text(item, tag, value):
    el=ET.SubElement(item,tag); el.text=value or ''


def append_item(channel,row):
    item=ET.SubElement(channel,'item')
    for tag,key in [('title','title'),('link','link'),('description','whatItDoes'),('pubDate','pubDate'),('source','source')]: set_text(item,tag,row.get(key,''))
    set_text(item,'category','legislation'); set_text(item,'region','')
    for tag in ('jurisdiction','status','whatItDoes','whoAffected','effectiveDate','nextStep','officialSource','billNumber','latestAction','sponsor'):
        set_text(item,tag,row.get(tag,''))
    set_text(item,'guid',hashlib.sha1(row['link'].encode()).hexdigest())


def main():
    if not NEWS.exists(): raise SystemExit('News feed not found')
    tree=ET.parse(NEWS); channel=tree.getroot().find('channel')
    if channel is None: raise SystemExit('RSS channel not found')
    federal_error=nm_error=None
    try: federal=fetch_federal()
    except Exception as exc: federal=[]; federal_error=exc
    try: nm=fetch_nm()
    except Exception as exc: nm=[]; nm_error=exc
    official=federal+nm
    if len(official)<10:
        print(f'Official legislation collector produced only {len(official)} records; preserving prior legislation. Federal={len(federal)} NM={len(nm)} federal_error={federal_error!r} nm_error={nm_error!r}')
        return
    for item in list(channel.findall('item')):
        if clean(item.findtext('category'))=='legislation': channel.remove(item)
    for row in official: append_item(channel,row)
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Official legislation collection v2: {len(federal)} Congress.gov + {len(nm)} New Mexico Legislature = {len(official)} official records. Current-session pool is not limited to 48 hours.')

if __name__=='__main__': main()
