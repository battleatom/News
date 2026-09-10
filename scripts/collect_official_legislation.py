from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NEWS = Path('News')
CONGRESS = 119
MAX_FEDERAL = 18
MAX_NM = 14
CONGRESS_API_KEY = os.environ.get('CONGRESS_API_KEY', 'DEMO_KEY')


def request_text(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 OfficialLegislationTracker/2.0'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='replace')


def request_json(url):
    return json.loads(request_text(url))


def clean(value):
    value = html.unescape(value or '')
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def iso_to_rfc(value):
    if not value:
        return format_datetime(datetime.now(timezone.utc))
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt.astimezone(timezone.utc))
    except Exception:
        try:
            dt = datetime.strptime(value[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            return format_datetime(dt)
        except Exception:
            return format_datetime(datetime.now(timezone.utc))


def status_from_action(action):
    t = (action or '').lower()
    if 'became public law' in t or 'signed by president' in t:
        return 'Signed / enacted'
    if 'veto' in t:
        return 'Vetoed'
    if 'passed senate' in t or 'passed house' in t or 'agreed to in senate' in t or 'agreed to in house' in t:
        return 'Passed a chamber'
    if 'reported by' in t or 'ordered to be reported' in t or 'committee' in t and 'reported' in t:
        return 'Advanced from committee'
    if 'introduced' in t or 'referred to' in t:
        return 'Introduced / referred'
    return 'Active in Congress'


def next_step_for(status):
    return {
        'Signed / enacted': 'Implementation, agency guidance, and any court challenges.',
        'Vetoed': 'Congress may attempt an override or lawmakers may introduce replacement legislation.',
        'Passed a chamber': 'Action in the other chamber, reconciliation of differences, and possible presidential signature.',
        'Advanced from committee': 'Possible floor consideration, amendments, or additional committee action.',
        'Introduced / referred': 'Committee hearings, markup, amendments, or further referral.',
        'Active in Congress': 'Watch the next recorded congressional action on the measure.',
    }.get(status, 'Watch the next formal action.')


def affected_from_text(text):
    t = (text or '').lower()
    groups = [
        ('Patients, providers, and health programs', ('health', 'medicaid', 'medicare', 'hospital', 'drug', 'medical')),
        ('Workers and employers', ('worker', 'labor', 'wage', 'union', 'employment')),
        ('Students, families, and schools', ('school', 'student', 'education', 'college', 'teacher')),
        ('Veterans, service members, and military families', ('veteran', 'military', 'armed forces', 'defense')),
        ('Taxpayers, households, and businesses', ('tax', 'budget', 'appropriation', 'spending', 'credit')),
        ('Immigrants and immigration agencies', ('immigration', 'immigrant', 'border', 'asylum', 'visa')),
        ('Tribal governments and Indigenous communities', ('tribal', 'native american', 'indian', 'navajo')),
        ('Consumers and regulated businesses', ('consumer', 'insurance', 'bank', 'financial', 'regulation')),
        ('Residents, utilities, and water users', ('water', 'utility', 'electric', 'energy', 'environment')),
    ]
    for label, terms in groups:
        if any(term in t for term in terms):
            return label
    return 'People, agencies, businesses, or programs covered by the measure'


def significant(title, summary, action):
    text = f'{title} {summary} {action}'.lower()
    low_value = ('commemorat', 'post office', 'naming', 'designat', 'coin', 'medal', 'recogniz')
    if any(x in text for x in low_value) and not any(x in text for x in ('budget', 'health', 'tax', 'military', 'rights', 'housing', 'immigration')):
        return False
    high_value = (
        'appropriation', 'budget', 'tax', 'health', 'medicaid', 'medicare', 'housing', 'immigration', 'border',
        'military', 'war powers', 'voting', 'election', 'privacy', 'surveillance', 'education', 'student', 'labor',
        'wage', 'energy', 'environment', 'water', 'tribal', 'native american', 'social security', 'benefit',
        'artificial intelligence', 'cyber', 'consumer', 'bank', 'insurance', 'drug', 'abortion', 'firearm',
        'passed', 'public law', 'veto', 'reported by', 'ordered to be reported'
    )
    return any(x in text for x in high_value)


def congress_url(bill_type, number):
    slugs = {
        'HR': 'house-bill', 'S': 'senate-bill', 'HJRES': 'house-joint-resolution',
        'SJRES': 'senate-joint-resolution', 'HCONRES': 'house-concurrent-resolution',
        'SCONRES': 'senate-concurrent-resolution', 'HRES': 'house-resolution', 'SRES': 'senate-resolution'
    }
    return f'https://www.congress.gov/bill/{CONGRESS}th-congress/{slugs.get(bill_type, "bill")}/{number}'


def fetch_federal():
    base = f'https://api.congress.gov/v3/bill/{CONGRESS}?format=json&limit=80&api_key={urllib.parse.quote(CONGRESS_API_KEY)}'
    data = request_json(base)
    rows = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=45)
    for bill in data.get('bills', []):
        if len(rows) >= MAX_FEDERAL:
            break
        btype = str(bill.get('type') or '').upper()
        number = str(bill.get('number') or '')
        title = clean(bill.get('title'))
        latest = bill.get('latestAction') or {}
        action = clean(latest.get('text'))
        action_date = latest.get('actionDate') or bill.get('updateDate') or ''
        try:
            dt = datetime.strptime(action_date[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if dt < cutoff:
                continue
        except Exception:
            pass
        summary = ''
        sponsor = ''
        try:
            detail = request_json(f'https://api.congress.gov/v3/bill/{CONGRESS}/{btype.lower()}/{number}?format=json&api_key={urllib.parse.quote(CONGRESS_API_KEY)}').get('bill', {})
            sponsors = detail.get('sponsors') or []
            if sponsors:
                sponsor = clean(sponsors[0].get('fullName') or sponsors[0].get('firstName', '') + ' ' + sponsors[0].get('lastName', ''))
        except Exception:
            pass
        try:
            summaries = request_json(f'https://api.congress.gov/v3/bill/{CONGRESS}/{btype.lower()}/{number}/summaries?format=json&api_key={urllib.parse.quote(CONGRESS_API_KEY)}').get('summaries', [])
            if summaries:
                summary = clean(summaries[-1].get('text'))
        except Exception:
            summary = ''
        if not significant(title, summary, action):
            continue
        url = congress_url(btype, number)
        status = status_from_action(action)
        rows.append({
            'title': f'{btype.replace("HJRES","H.J.Res.").replace("SJRES","S.J.Res.").replace("HCONRES","H.Con.Res.").replace("SCONRES","S.Con.Res.").replace("HRES","H.Res.").replace("SRES","S.Res.")} {number} — {title}',
            'link': url,
            'source': 'Congress.gov',
            'pubDate': iso_to_rfc(action_date),
            'jurisdiction': 'Federal',
            'status': status,
            'whatItDoes': summary or title,
            'whoAffected': affected_from_text(f'{title} {summary}'),
            'effectiveDate': 'See enacted text if the measure becomes law',
            'nextStep': next_step_for(status),
            'officialSource': url,
            'billNumber': f'{btype} {number}',
            'latestAction': action or 'No latest action text returned',
            'sponsor': sponsor,
        })
    return rows


class NMSearchParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False
        self.row_parts = []
        self.rows = []
        self.current_href = ''
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.in_row = True
            self.row_parts = []
            self.current_href = ''
        if self.in_row and tag == 'a':
            href = attrs.get('href', '')
            if '/Legislation/' in href or '/legislation/' in href:
                self.current_href = href
    def handle_data(self, data):
        if self.in_row:
            text = clean(data)
            if text:
                self.row_parts.append(text)
    def handle_endtag(self, tag):
        if tag == 'tr' and self.in_row:
            self.in_row = False
            text = ' | '.join(self.row_parts)
            if self.current_href and re.search(r'\b(?:HB|SB|HJR|SJR|HM|SM|HR|SR)\s*\d+\b', text, re.I):
                self.rows.append((self.current_href, text))


def fetch_nm():
    # This is the official NM Legislature search database. Query=To: returns the complete current indexed legislation list.
    raw = request_text('https://www.nmlegis.gov/Search?Query=To%3A')
    parser = NMSearchParser()
    parser.feed(raw)
    rows = []
    for href, text in parser.rows:
        if len(rows) >= MAX_NM:
            break
        if '2026 Regular' not in text:
            continue
        m = re.search(r'\b(HB|SB|HJR|SJR|HM|SM|HR|SR)\s*(\d+)\b', text, re.I)
        if not m:
            continue
        bill_id = f'{m.group(1).upper()} {m.group(2)}'
        parts = [p.strip() for p in text.split('|') if p.strip()]
        try:
            idx = next(i for i,p in enumerate(parts) if re.fullmatch(r'\*?\s*'+re.escape(m.group(1))+r'\s*'+re.escape(m.group(2)), p, re.I))
        except StopIteration:
            idx = 0
        title = parts[idx+1] if idx+1 < len(parts) else bill_id
        full_text = ' '.join(parts)
        status = 'Active / pending'
        for candidate in ('Chaptered', 'Signed', 'Vetoed', 'Passed House and Senate', 'Passed Senate', 'Passed House', 'Died', 'Substituted'):
            if candidate.lower() in full_text.lower():
                status = candidate
                break
        if status in ('Died', 'Substituted'):
            continue
        if not significant(title, '', status):
            continue
        if href.startswith('/'):
            href = 'https://www.nmlegis.gov' + href
        elif not href.startswith('http'):
            href = 'https://www.nmlegis.gov/' + href.lstrip('/')
        sponsor = ''
        if idx+2 < len(parts):
            sponsor = parts[idx+2]
        rows.append({
            'title': f'{bill_id} — {title}',
            'link': href,
            'source': 'New Mexico Legislature',
            'pubDate': format_datetime(datetime.now(timezone.utc)),
            'jurisdiction': 'New Mexico',
            'status': status,
            'whatItDoes': title.title() if title.isupper() else title,
            'whoAffected': affected_from_text(title),
            'effectiveDate': 'See official bill text / chaptered law',
            'nextStep': 'Implementation and effective-date tracking.' if status in ('Chaptered', 'Signed') else 'Watch the next committee, floor, or governor action.',
            'officialSource': href,
            'billNumber': bill_id,
            'latestAction': status,
            'sponsor': sponsor,
        })
    return rows


def set_text(item, tag, value):
    el = ET.SubElement(item, tag)
    el.text = value or ''


def append_item(channel, row):
    item = ET.SubElement(channel, 'item')
    set_text(item, 'title', row['title'])
    set_text(item, 'link', row['link'])
    set_text(item, 'description', row['whatItDoes'])
    set_text(item, 'pubDate', row['pubDate'])
    set_text(item, 'source', row['source'])
    set_text(item, 'category', 'legislation')
    set_text(item, 'region', '')
    set_text(item, 'jurisdiction', row['jurisdiction'])
    set_text(item, 'status', row['status'])
    set_text(item, 'whatItDoes', row['whatItDoes'])
    set_text(item, 'whoAffected', row['whoAffected'])
    set_text(item, 'effectiveDate', row['effectiveDate'])
    set_text(item, 'nextStep', row['nextStep'])
    set_text(item, 'officialSource', row['officialSource'])
    set_text(item, 'billNumber', row.get('billNumber', ''))
    set_text(item, 'latestAction', row.get('latestAction', ''))
    set_text(item, 'sponsor', row.get('sponsor', ''))


def main():
    if not NEWS.exists():
        raise SystemExit('News feed not found')
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')

    federal, nm = [], []
    federal_error = nm_error = None
    try:
        federal = fetch_federal()
    except Exception as exc:
        federal_error = exc
    try:
        nm = fetch_nm()
    except Exception as exc:
        nm_error = exc

    official = federal + nm
    if not official:
        print(f'Official legislation collection returned no records; preserving existing legislation. Congress error={federal_error!r}; NM error={nm_error!r}')
        return

    for item in list(channel.findall('item')):
        if clean(item.findtext('category')) == 'legislation':
            channel.remove(item)
    for row in official:
        append_item(channel, row)

    tree.write(NEWS, encoding='utf-8', xml_declaration=True)
    print(f'Official legislation collection: {len(federal)} Congress.gov records + {len(nm)} NM Legislature records. News is supporting coverage only.')
    if federal_error:
        print(f'Congress.gov warning: {federal_error!r}')
    if nm_error:
        print(f'NM Legislature warning: {nm_error!r}')


if __name__ == '__main__':
    main()
