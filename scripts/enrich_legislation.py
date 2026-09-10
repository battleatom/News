from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NEWS = Path('News')
MAX_SUPPORTING = 4
SUPPORTING_MAX_AGE_DAYS = 120
BLOCKED_PAYWALL = ('new york times','the new york times','wall street journal','wsj','bloomberg','washington post','the washington post','barron')
OFFICIAL_SOURCES = ('congress.gov','congress gov','federal register','federalregister.gov','white house','whitehouse.gov','new mexico legislature','nmlegis.gov','governor of new mexico','farmington nm','san juan county')
JOURNALISM_SOURCES = (
    'associated press','ap news','reuters','npr','pbs','abc news','cbs news','nbc news','cnn','fox news','usa today',
    'axios','politico','the hill','the guardian','propublica','kff health news','inside climate','grist','reveal',
    'source new mexico','new mexico in depth','searchlight new mexico','santa fe new mexican','albuquerque journal',
    'tri-city record','farmington daily times','ksje','navajo times','durango herald','the journal','colorado public radio',
    'stateline','states newsroom','public radio','newsweek','time',
)


def clean(value):
    value = html.unescape(value or '')
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def feed_url(query):
    q = urllib.parse.quote(query)
    return f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'


def words(text):
    stop={'the','a','an','to','of','in','on','for','and','with','is','as','at','from','by','after','new','says','said','that','this','are','was','were','has','have','had','into','over','its','their','will','amid','more','than'}
    return {w for w in re.findall(r'[a-z0-9]+',(text or '').lower()) if len(w)>=4 and w not in stop}


def source_is_paywalled(source):
    s=(source or '').lower()
    return any(x in s for x in BLOCKED_PAYWALL)


def source_is_journalism(source):
    s=(source or '').lower()
    return any(x in s for x in JOURNALISM_SOURCES)


def parse_pubdate(pub):
    try:
        return parsedate_to_datetime(pub).astimezone(timezone.utc)
    except Exception:
        return None


def fetch_supporting(title, primary_link, bill_number=''):
    terms=[w for w in re.findall(r'[A-Za-z0-9]+',title) if len(w)>3][:14]
    query=' '.join(([bill_number] if bill_number else []) + terms)
    if not query.strip():
        return []
    try:
        req=urllib.request.Request(feed_url(query),headers={'User-Agent':'Mozilla/5.0 LegislationTracker/2.0'})
        with urllib.request.urlopen(req,timeout=15) as response:
            root=ET.fromstring(response.read())
    except Exception:
        return []
    target=words(title)
    rows=[]; seen=set(); cutoff=datetime.now(timezone.utc)-timedelta(days=SUPPORTING_MAX_AGE_DAYS)
    for item in root.findall('.//item'):
        t=clean(item.findtext('title')); link=clean(item.findtext('link')); desc=clean(item.findtext('description'))
        source_el=item.find('source'); source=clean(source_el.text if source_el is not None else '')
        pub=clean(item.findtext('pubDate')); dt=parse_pubdate(pub)
        if not t or not link or link==primary_link or source_is_paywalled(source) or not source_is_journalism(source):
            continue
        overlap=len(target & words(t))
        if bill_number and bill_number.lower().replace(' ','') in t.lower().replace(' ',''):
            overlap += 3
        if overlap<2 or not dt or dt<cutoff:
            continue
        sk=re.sub(r'[^a-z0-9]','',source.lower()) or link
        if sk in seen:
            continue
        seen.add(sk)
        age_days=max(0,(datetime.now(timezone.utc)-dt).days)
        rows.append((overlap*10-max(0,age_days/14),t,link,source,pub,desc))
    rows.sort(key=lambda x:x[0],reverse=True)
    return rows[:MAX_SUPPORTING]


def jurisdiction(text):
    t=text.lower()
    if any(x in t for x in ('new mexico','nm legislature','nmlegis','state legislature')):
        return 'New Mexico'
    if any(x in t for x in ('farmington','san juan county','city council','county commission','ordinance','durango','cortez','montezuma county','la plata county')):
        return 'Local / Four Corners'
    return 'Federal'


def status(text):
    t=text.lower()
    if any(x in t for x in ('signed into law','signs bill','signed bill','enacted','became public law')): return 'Signed / enacted'
    if 'veto' in t: return 'Vetoed'
    if any(x in t for x in ('passes house','house passes','passes senate','senate passes','passed the house','passed the senate')): return 'Passed a chamber'
    if any(x in t for x in ('committee advances','advances bill','clears committee','reported by','ordered to be reported')): return 'Advanced from committee'
    if any(x in t for x in ('introduced','referred to','proposed rule','proposal')): return 'Introduced / referred'
    return 'Active development'


def affected(text):
    t=text.lower()
    groups=[
        ('Patients, providers, and health programs',('medicaid','medicare','hospital','health care','healthcare','drug price')),
        ('Workers and employers',('worker','labor','wage','overtime','union','workplace')),
        ('Students, families, and schools',('school','student','teacher','education','college')),
        ('Veterans, service members, and military families',('veteran','military','service member','va ')),
        ('Taxpayers, households, and businesses',('tax','budget','spending','credit','deduction')),
        ('Consumers and regulated businesses',('consumer','fee','insurance','antitrust','regulation')),
        ('Immigrants and immigration agencies',('immigration','immigrant','border','asylum','visa','h-1b')),
        ('Tribal governments and Indigenous communities',('tribal','navajo','indigenous','native american')),
        ('Residents, utilities, and water users',('water','utility','electric','pollution','environment')),
    ]
    for label,terms in groups:
        if any(term in t for term in terms): return label
    return 'People and organizations subject to the measure'


def next_step(status_text):
    return {
        'Signed / enacted':'Implementation and any agency guidance or court challenges.',
        'Vetoed':'Watch for an override attempt, replacement legislation, or renewed proposal.',
        'Passed a chamber':'Action in the other chamber, reconciliation, or executive signature.',
        'Advanced from committee':'A floor vote or additional committee action.',
        'Introduced / referred':'Committee hearings, amendments, or a floor vote.',
    }.get(status_text,'Watch for the next formal vote, order, rulemaking step, or implementation action.')


def set_text(item,tag,value):
    el=item.find(tag)
    if el is None:
        el=ET.SubElement(item,tag)
    el.text=value


def keep_or(item, tag, fallback):
    current=clean(item.findtext(tag))
    return current or fallback


def main():
    if not NEWS.exists(): raise SystemExit('News feed not found')
    tree=ET.parse(NEWS); root=tree.getroot(); channel=root.find('channel')
    if channel is None: raise SystemExit('RSS channel not found')
    count=0; support_count=0; official_count=0
    for item in channel.findall('item'):
        if clean(item.findtext('category'))!='legislation': continue
        title=clean(item.findtext('title')); desc=clean(item.findtext('description')); link=clean(item.findtext('link'))
        source=clean(item.findtext('source')); text=f'{title} {desc} {source} {clean(item.findtext("latestAction"))}'
        st=keep_or(item,'status',status(text))
        set_text(item,'jurisdiction',keep_or(item,'jurisdiction',jurisdiction(text)))
        set_text(item,'status',st)
        set_text(item,'whatItDoes',keep_or(item,'whatItDoes',desc if len(desc)>=45 else title))
        set_text(item,'whoAffected',keep_or(item,'whoAffected',affected(text)))
        set_text(item,'effectiveDate',keep_or(item,'effectiveDate','See official text'))
        set_text(item,'nextStep',keep_or(item,'nextStep',next_step(st)))
        official=keep_or(item,'officialSource',link if any(x in source.lower() for x in OFFICIAL_SOURCES) else '')
        set_text(item,'officialSource',official)
        if official: official_count+=1
        bill_number=clean(item.findtext('billNumber'))
        supporting=fetch_supporting(title,link,bill_number)
        for existing in list(item.findall('relatedArticles')): item.remove(existing)
        if supporting:
            rel=ET.SubElement(item,'relatedArticles')
            for _,t,l,src,pub,d in supporting:
                ar=ET.SubElement(rel,'article')
                ET.SubElement(ar,'title').text=t; ET.SubElement(ar,'link').text=l; ET.SubElement(ar,'source').text=src
                ET.SubElement(ar,'pubDate').text=pub; ET.SubElement(ar,'description').text=d; support_count+=1
        count+=1
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Legislation enrichment complete: {count} official-record cards; {official_count} official links preserved; {support_count} supporting news links attached.')

if __name__=='__main__': main()
