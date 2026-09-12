#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import html as html_lib
import re
import xml.etree.ElementTree as ET

import update_news_v4 as v4

core=v4.core
NEWS=Path('News')
CLEAN_LIMIT=20
DIRTY_LIMIT=22
ADULT_MIN=8

PREVIEW_SOURCES=[
    ('People','site:people.com actor actress singer musician celebrity baby pregnancy birth wedding engagement philanthropy charity entertainment'),
    ('E! News','site:eonline.com actor actress singer musician celebrity entertainment awards family baby pregnancy philanthropy'),
    ('Variety','site:variety.com actor actress director Hollywood television film entertainment'),
    ('Billboard','site:billboard.com music artist singer rapper musician tour album'),
    ('Deadline','site:deadline.com actor actress director television film Hollywood'),
    ('The Hollywood Reporter','site:hollywoodreporter.com actor actress director film television entertainment'),
    ('Rolling Stone','site:rollingstone.com actor actress singer musician artist entertainment'),
    ('Entertainment Weekly','site:ew.com actor actress singer musician celebrity entertainment'),
]

DIRTY_PREVIEW_SOURCES=[
    ('Page Six','site:pagesix.com celebrity dating breakup feud nude topless bikini swimsuit sheer see-through red carpet'),
    ('People','site:people.com celebrity dating breakup bikini swimsuit sheer nude topless red carpet'),
    ('E! News','site:eonline.com celebrity dating breakup bikini swimsuit sheer nude red carpet fashion'),
    ('TMZ','site:tmz.com celebrity dating breakup feud nude onlyfans porn star adult performer'),
]

# Broad A-list / household-name seed. This is only a prominence boost, never a whitelist.
# Dynamic cross-source coverage below can elevate any currently hot actor, actress,
# musician or artist even when they are not in this seed set.
MAJOR_NAMES={
    'adele','ariana grande','bad bunny','beyonce','billie eilish','bruno mars','cardi b',
    'chappell roan','doja cat','drake','dua lipa','ed sheeran','harry styles','justin bieber',
    'katy perry','kendrick lamar','lady gaga','lizzo','miley cyrus','nicki minaj','olivia rodrigo',
    'rihanna','sabrina carpenter','selena gomez','shakira','sza','taylor swift','the weeknd',
    'travis scott','usher','post malone','megan thee stallion','jennifer lopez','madonna',
    'angelina jolie','anne hathaway','austin butler','ben affleck','brad pitt','chris evans',
    'chris hemsworth','cillian murphy','colin farrell','dwayne johnson','emma stone','florence pugh',
    'gal gadot','george clooney','glen powell','hugh jackman','jake gyllenhaal','jenna ortega',
    'jennifer aniston','jennifer lawrence','joaquin phoenix','johnny depp','keanu reeves',
    'leonardo dicaprio','margot robbie','matt damon','meryl streep','michael b jordan',
    'millie bobby brown','natalie portman','nicole kidman','pedro pascal','reese witherspoon',
    'robert downey jr','ryan gosling','ryan reynolds','sandra bullock','scarlett johansson',
    'sydney sweeney','timothee chalamet','tom cruise','tom holland','viola davis','will smith',
    'zendaya','zoe saldana','ana de armas','dakota johnson','demi moore','pamela anderson',
}

# 2026 XMA/XMA Creator winners are used only as a Dirty-feed prominence boost.
ADULT_PROMINENCE={
    'jennifer white':90,'vince karter':90,'ariel demure':90,'sophia locke':80,
    'octavia red':80,'derek kage':80,'cubbi thompson':75,'emma magnolia':75,
    'girthmasterr':75,'serenity cox':70,'elly clutch':70,'hayley quinn':65,
    'nakedbakers':65,'coal daniels':65,'sarina havok':65,'victoria peach':65,
    'bunnydollstella':65,'felicia hardy':60,'casey kisses':60,'kylie le beau':60,
    'zariah aura':60,'codi vore':60,'leigh raven':60,'katie summer':60,
}

ADULT_SOURCE_TOKENS=('xbiz','avn')
SPECIALIST_CLEAN_SOURCES=('variety','billboard','deadline','hollywood reporter','rolling stone','entertainment weekly','e! news','people')
REJECT_TERMS=('horoscope','astrology','fan theory','fan theories','death hoax','fake death','lookalike')
FILLER_TERMS=('review:',' review','predictions','prediction:','full list','complete list','specialty preview','festival preview','preview:','roundup','ranked list','best movies','best shows','what to watch','explained:')
GENERIC_NONCELEB_TERMS=('officer','police officer','deputy','mom of','dad of','woman charged','man charged','woman indicted','man indicted','teacher arrested','student arrested')
ENT_ROLE_TERMS=('actor','actress','singer','rapper','musician','artist','director','filmmaker','comedian','performer','dj','screenwriter','voice actor','songwriter','supermodel','model','movie star','tv star','television star','recording artist')
EXPLICIT_SKIP=('gangbang','anal scene','first anal','sex toy','stroker','dildo','sex doll','masturbator','hardcore','blowjob','oral scene','double penetration')
XBIZ_KEEP_HINTS=('performer','star','actress','actor','award','wins','winner','interview','podcast','launch','platform','business','company','studio','industry','legal','lawsuit','court','regulation','compliance','creator','onlyfans','fansly','model','agency','director','producer','executive','joins','hired','signs','deal','event','conference','expands','partnership','acquires')

MAJOR_TERMS=('dies','died','death','dead','hospitalized','hospitalised','cancer','serious illness','injury','arrested','arrest','charged','indicted','lawsuit','sued','abuse','assault','harassment','investigation','strike','bankruptcy','shutdown','closure','layoffs')
CAREER_TERMS=('cast','casting','joins','starring','role','movie','film','series','renewed','renewal','canceled','cancelled','premiere','release','album','single','tour','concert','contract','deal','signs','retire','retirement','debut','box office')
FAMILY_TERMS=('baby','pregnant','pregnancy','gave birth','gives birth','welcomes son','welcomes daughter','newborn','children','kids','family','engaged','engagement','married','wedding')
PHILANTHROPY_TERMS=('charity','philanthropy','foundation','donation','fundraiser','fundraising','benefit gala')
MAINSTREAM_AWARD_TERMS=('oscar','oscars','emmy','emmys','grammy','grammys','golden globe','sag award')
RELATIONSHIP_TERMS=('dating','boyfriend','girlfriend','romance','romantic','new couple','relationship')
GOSSIP_TERMS=('breakup','break-up','split','cheating','affair','feud','gossip','rumor','rumour','spotted with')
MATURE_FASHION_TERMS=('bikini','swimsuit','sheer','see-through','see through','braless','plunging','wardrobe malfunction')
NUDE_TERMS=('nude','naked','topless','photo shoot','photoshoot','nude scene')
ADULT_TERMS=('adult film','adult entertainment','porn star','pornstar','porn performer','adult performer','onlyfans','fansly','pornhub','xbiz','avn')
ADULT_AWARD_TERMS=('xma','xmas','avn award','adult award')
BUSINESS_LEGAL_TERMS=('lawsuit','sued','court','legal','regulation','law','business','company','platform','studio','contract','deal','acquires','acquisition','ban','payment','compliance')

ENTITY_NOISE={
    'People','People Com','E News','Variety','Billboard','Deadline','The Hollywood Reporter',
    'Rolling Stone','Entertainment Weekly','New York','Los Angeles','United States','North Carolina',
    'South Korean','Prime Video','Netflix','Toronto Film Festival','White House','Associated Press',
}


def _text(item):
    return f"{item.get('title','')} {item.get('description','')} {item.get('source','')}".lower()

def _title(item):
    return (item.get('title') or '').strip()

def _title_lower(item):
    return _title(item).lower()

def _key(item):
    try:return core.key(item)
    except Exception:return (item.get('link') or item.get('title') or '').strip().lower()

def _published(item):
    p=item.get('published')
    if isinstance(p,datetime):return p
    try:return datetime.fromisoformat(str(p))
    except Exception:return datetime.min.replace(tzinfo=timezone.utc)

def _source_key(item):
    return (item.get('source') or '').strip().lower()

def _source_is_adult(item):
    return any(t in _source_key(item) for t in ADULT_SOURCE_TOKENS)

def _adult_prominence(item):
    text=_text(item)
    return max([score for name,score in ADULT_PROMINENCE.items() if name in text] or [0])

def _known_name(item):
    text=_text(item)
    matches=[name for name in MAJOR_NAMES if name in text]
    return max(matches,key=len) if matches else ''

def _title_entities(item):
    title=_title(item)
    # Conservative proper-name extraction: two to four title-case words. The
    # dynamic signal only counts an entity when distinct outlets repeat it.
    matches=re.findall(r"\b(?:[A-Z][A-Za-z'’.-]+)(?:\s+(?:[A-Z][A-Za-z'’.-]+)){1,3}\b",title)
    out=[]
    for raw in matches:
        raw=raw.strip(' -–—:,.')
        if raw in ENTITY_NOISE or len(raw)<5:
            continue
        if any(noise.lower()==raw.lower() for noise in ENTITY_NOISE):
            continue
        out.append(raw.lower())
    return set(out)

def build_clean_signals(candidates):
    entity_sources={}
    for item in candidates:
        if _source_is_adult(item):
            continue
        src=_source_key(item)
        for entity in _title_entities(item):
            entity_sources.setdefault(entity,set()).add(src)
    return entity_sources

def _dynamic_prominence(item,entity_sources):
    best=0
    for entity in _title_entities(item):
        n=len(entity_sources.get(entity,set()))
        if n>=5:best=max(best,220)
        elif n==4:best=max(best,180)
        elif n==3:best=max(best,145)
        elif n==2:best=max(best,95)
    if _known_name(item):
        best=max(best,175)
    return best

def _story_coverage(item,candidates):
    sources=set()
    for other in candidates:
        if _source_is_adult(other):
            continue
        if _key(other)==_key(item):
            sources.add(_source_key(other));continue
        try:
            same=v4._same_entertainment_event(item,other)
        except Exception:
            same=False
        if same:sources.add(_source_key(other))
    n=len(sources)
    if n>=5:return 150
    if n==4:return 120
    if n==3:return 90
    if n==2:return 55
    return 0

def _clean_relevant(item,cls,prominence):
    title=_title_lower(item)
    source=_source_key(item)
    if any(term in title for term in FILLER_TERMS):
        return False
    has_known=bool(_known_name(item))
    has_role=any(term in title for term in ENT_ROLE_TERMS)
    repeated=prominence>=95
    specialist=any(token in source for token in SPECIALIST_CLEAN_SOURCES)
    has_person=bool(_title_entities(item))

    # Generic human-interest/crime stories from People-style sources are not
    # Entertainment unless an actual entertainment figure is identifiable.
    if any(term in title for term in GENERIC_NONCELEB_TERMS) and not (has_known or has_role or repeated):
        return False

    # Strong named-person gate. Major/career/family stories from a specialist
    # outlet can pass with a proper name; generic ENTERTAINMENT filler cannot.
    if has_known or repeated or has_role:
        return True
    if specialist and has_person and cls in {'MAJOR','PEOPLE / FAMILY','CAREER','AWARDS','PHILANTHROPY'}:
        return True
    return False

def classify(item,forced_dirty=False,adult_source=False):
    text=_text(item)
    title=_title_lower(item)
    if any(t in text for t in REJECT_TERMS):return None
    adult=adult_source or any(t in text for t in ADULT_TERMS)
    if adult:
        if any(t in text for t in ADULT_AWARD_TERMS):cls='ADULT AWARDS'
        elif any(t in text for t in BUSINESS_LEGAL_TERMS):cls='ADULT BUSINESS/LEGAL'
        elif 'onlyfans' in text or 'fansly' in text or 'creator' in text:cls='CREATOR'
        else:cls='ADULT INDUSTRY'
        return 'dirty',cls
    if any(t in title for t in NUDE_TERMS):return 'dirty','NUDE / PHOTO SHOOT'
    if any(t in title for t in MATURE_FASHION_TERMS):return 'dirty','MATURE FASHION'
    if any(t in title for t in GOSSIP_TERMS):return 'dirty','GOSSIP'
    if any(t in title for t in RELATIONSHIP_TERMS):return 'dirty','RELATIONSHIPS'
    if forced_dirty:return 'dirty','GOSSIP / LIFESTYLE'
    if any(t in title for t in MAJOR_TERMS):return 'clean','MAJOR'
    if any(t in title for t in FAMILY_TERMS):return 'clean','PEOPLE / FAMILY'
    if any(t in title for t in PHILANTHROPY_TERMS):return 'clean','PHILANTHROPY'
    if any(t in title for t in MAINSTREAM_AWARD_TERMS):return 'clean','AWARDS'
    if any(t in title for t in CAREER_TERMS):return 'clean','CAREER'
    return 'clean','ENTERTAINMENT'

def score_item(item,safety,cls,prominence=0,coverage=0):
    title=_title_lower(item)
    if safety=='clean':
        base={'MAJOR':620,'PEOPLE / FAMILY':560,'CAREER':535,'AWARDS':510,'PHILANTHROPY':455,'ENTERTAINMENT':330}.get(cls,300)
        base+=prominence+coverage
        if any(t in title for t in ('gave birth','gives birth','welcomes','baby','pregnant','pregnancy')):base+=45
        if _known_name(item):base+=35
    else:
        base={'ADULT BUSINESS/LEGAL':1000,'ADULT INDUSTRY':920,'CREATOR':880,'ADULT AWARDS':850,'NUDE / PHOTO SHOOT':760,'MATURE FASHION':700,'GOSSIP':650,'RELATIONSHIPS':625,'GOSSIP / LIFESTYLE':600}.get(cls,600)
        base+=_adult_prominence(item)
        if any(t in title for t in MAJOR_TERMS):base+=120
    if _source_is_adult(item):base+=35
    return base

def decorate(item,entity_sources,candidates,forced_dirty=False,adult_source=False):
    tagged=classify(item,forced_dirty=forced_dirty,adult_source=adult_source)
    if not tagged:return None
    safety,cls=tagged
    copy=dict(item)
    if safety=='clean':
        prominence=_dynamic_prominence(copy,entity_sources)
        if not _clean_relevant(copy,cls,prominence):
            return None
        coverage=_story_coverage(copy,candidates)
        copy['entertainmentProminence']=prominence
        copy['entertainmentCoverage']=coverage
    else:
        prominence=_adult_prominence(copy)
        coverage=0
        copy['entertainmentProminence']=prominence
        copy['entertainmentCoverage']=''
    copy['entertainmentSafety']=safety
    copy['entertainmentLabel']=cls
    copy['entertainmentScore']=score_item(copy,safety,cls,prominence,coverage)
    copy['entertainmentTier']='under-the-radar' if safety=='dirty' else 'ranked'
    if safety=='dirty' and (adult_source or cls in {'ADULT INDUSTRY','ADULT BUSINESS/LEGAL','CREATOR','ADULT AWARDS','NUDE / PHOTO SHOOT'}):copy['imageUrl']=''
    return copy

def _strip_tags(value):
    value=re.sub(r'<[^>]+>',' ',value or '')
    value=html_lib.unescape(value)
    return re.sub(r'\s+',' ',value).strip()

def _parse_xbiz_date(fragment):
    m=re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\b',fragment)
    if not m:return None
    try:return datetime.strptime(m.group(0),'%b %d, %Y').replace(tzinfo=timezone.utc)
    except Exception:return None

def fetch_xbiz_direct(limit=20):
    url='https://www.xbiz.com/news/'
    try:
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; UnderreportedV4/1.0)'})
        raw=urlopen(req,timeout=20).read().decode('utf-8','ignore')
    except Exception as exc:
        print('XBIZ direct fallback failed:',exc);return []
    found=[];seen=set()
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']*/news/\d+/[^"\']+)["\'][^>]*>(.*?)</a>',raw,re.I|re.S):
        href=html_lib.unescape(m.group(1));title=_strip_tags(m.group(2))
        if len(title)<12:continue
        low=title.lower()
        if any(t in low for t in EXPLICIT_SKIP):continue
        if not any(t in low for t in XBIZ_KEEP_HINTS):continue
        link=urljoin(url,href)
        if link in seen:continue
        nearby=raw[max(0,m.start()-700):min(len(raw),m.end()+900)]
        published=_parse_xbiz_date(_strip_tags(nearby))
        if published is None:continue
        seen.add(link)
        found.append({'title':title,'link':link,'description':f'XBIZ reports an adult-entertainment industry development involving {title}.','pubDate':format_datetime(published),'published':published,'source':'XBIZ','category':'entertainment','imageUrl':'','_adult_source':True})
        if len(found)>=limit:break
    print(f'entertainment dirty/XBIZ direct: {len(found)} accepted')
    return found

def dedupe_rank(items,limit,mode):
    ranked=sorted(items,key=lambda x:(int(x.get('entertainmentScore') or 0),_published(x)),reverse=True)
    out=[];seen=set();source_counts={}
    for item in ranked:
        if item.get('entertainmentSafety')!=mode:continue
        k=_key(item);src=_source_key(item)
        cap=10 if src in ADULT_SOURCE_TOKENS else 5
        if not k or k in seen or source_counts.get(src,0)>=cap:continue
        if any(v4._same_entertainment_event(prior,item) for prior in out):continue
        seen.add(k);source_counts[src]=source_counts.get(src,0)+1;out.append(item)
        if len(out)>=limit:break
    return out

def collect():
    candidates=[]
    query=core.QUERIES.get('entertainment',[])
    combined=' OR '.join(f'({q})' for q in query) if isinstance(query,list) else query
    try:
        batch=core.parse_items(core.fetch(combined),'entertainment');candidates.extend(batch)
        print(f'entertainment primary: {len(batch)} accepted')
    except Exception as exc:print('Entertainment primary feed failed:',exc)
    for source,q in PREVIEW_SOURCES:
        try:
            batch=core.parse_items(core.fetch(q),'entertainment',source_override=source);candidates.extend(batch)
            print(f'entertainment clean-source/{source}: {len(batch)} accepted')
        except Exception as exc:print(f'Entertainment preview failed for {source}: {exc}')
    for source,q in DIRTY_PREVIEW_SOURCES:
        try:
            batch=core.parse_items(core.fetch(q),'entertainment',source_override=source)
            tagged=[]
            for x in batch:
                y=dict(x);y['_forced_dirty']=True;tagged.append(y)
            candidates.extend(tagged)
            print(f'entertainment dirty-source/{source}: {len(batch)} accepted')
        except Exception as exc:print(f'Entertainment dirty preview failed for {source}: {exc}')
    direct=fetch_xbiz_direct();candidates.extend(direct)

    entity_sources=build_clean_signals(candidates)
    decorated=[]
    for item in candidates:
        d=decorate(item,entity_sources,candidates,forced_dirty=bool(item.get('_forced_dirty')),adult_source=bool(item.get('_adult_source')) or _source_is_adult(item))
        if d:decorated.append(d)

    clean=dedupe_rank(decorated,CLEAN_LIMIT,'clean')
    dirty=dedupe_rank(decorated,DIRTY_LIMIT,'dirty')
    adult=[x for x in dirty if x.get('entertainmentLabel') in {'ADULT INDUSTRY','ADULT BUSINESS/LEGAL','CREATOR','ADULT AWARDS'}]
    if len(adult)<ADULT_MIN:
        extras=dedupe_rank([x for x in decorated if x.get('entertainmentSafety')=='dirty' and x.get('entertainmentLabel') in {'ADULT INDUSTRY','ADULT BUSINESS/LEGAL','CREATOR','ADULT AWARDS'}],ADULT_MIN,'dirty')
        keys={_key(x) for x in dirty}
        for x in extras:
            if _key(x) not in keys:
                dirty.append(x);keys.add(_key(x))
        dirty=sorted(dirty,key=lambda x:(int(x.get('entertainmentScore') or 0),_published(x)),reverse=True)[:DIRTY_LIMIT]

    print('Selected Entertainment stories:',len(clean)+len(dirty))
    print('  Clean:',len(clean))
    print('  Dirty-only:',len(dirty))
    print('  Adult-industry:',sum(1 for x in dirty if x.get('entertainmentLabel') in {'ADULT INDUSTRY','ADULT BUSINESS/LEGAL','CREATOR','ADULT AWARDS'}))
    for idx,item in enumerate(clean[:10],1):
        print(f"  Clean #{idx}: score={item.get('entertainmentScore')} prominence={item.get('entertainmentProminence')} coverage={item.get('entertainmentCoverage')} {item.get('entertainmentLabel')} - {item.get('title')}")
    if dirty:print('  Dirty top:',dirty[0].get('entertainmentLabel'),'-',dirty[0].get('title'))
    return clean+dirty

def append_node(channel,item):
    n=ET.Element('item')
    def add(tag,val):e=ET.SubElement(n,tag);e.text=str(val or '')
    add('title',item.get('title'));add('link',item.get('link'));add('description',item.get('description'));add('pubDate',item.get('pubDate'));add('source',item.get('source'));add('category','entertainment');add('region','');add('state','');add('imageUrl',item.get('imageUrl',''));add('entertainmentTier',item.get('entertainmentTier',''));add('entertainmentSafety',item.get('entertainmentSafety','clean'));add('entertainmentLabel',item.get('entertainmentLabel','ENTERTAINMENT'));add('entertainmentScore',item.get('entertainmentScore',''));add('entertainmentProminence',item.get('entertainmentProminence',''));add('entertainmentCoverage',item.get('entertainmentCoverage',''));add('whyMatters','Why it matters: It may affect careers, audiences, families, creators, productions, business, or the wider entertainment industry.')
    channel.append(n)

def main():
    if not NEWS.exists():raise SystemExit('News feed not found')
    selected=collect()
    if not selected:raise SystemExit('No verified Entertainment stories were collected')
    tree=ET.parse(NEWS);root=tree.getroot();channel=root.find('channel')
    if channel is None:raise SystemExit('RSS channel missing')
    for node in list(channel.findall('item')):
        if (node.findtext('category') or '').strip().lower()=='entertainment':channel.remove(node)
    for item in selected:append_node(channel,item)
    last=channel.find('lastBuildDate')
    if last is not None:last.text=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Wrote {len(selected)} Entertainment stories to News')

if __name__=='__main__':main()
