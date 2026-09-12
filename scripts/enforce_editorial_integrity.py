#!/usr/bin/env python3
"""Final editorial-integrity pass for V4.

Runs after generic routing/deduplication and after X is rebuilt. It is intentionally
conservative: obvious U.S. domestic leakage is removed from World, ordinary sports
leakage is kept out of the U.S. tab, generic/non-story pages are dropped, weak Related
Coverage links are pruned, low-value Technology shopping/gaming leakage is corrected,
and fixed X slots are repaired from already verified feed stories when their lead is
not relevant to the slot.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from filter_landing_pages import is_landing_page

NEWS = Path('News')

STOP = {
    'the','a','an','and','or','but','for','from','with','into','over','after','before','about','amid','during',
    'this','that','these','those','says','said','say','new','news','latest','update','report','reports','reported',
    'according','officials','official','will','could','would','may','can','has','have','had','was','were','are','is',
    'be','been','being','to','of','in','on','at','by','as','it','its','their','they','them','who','what','when','where',
    'why','how','one','two','first','second','today','now','more','just','also','still','live','coverage'
}
US_STATES = {
    'alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii',
    'idaho','illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan',
    'minnesota','mississippi','missouri','montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york',
    'north carolina','north dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina','south dakota',
    'tennessee','texas','utah','vermont','virginia','washington','west virginia','wisconsin','wyoming'
}
FOREIGN = {
    'canada','canadian','mexico','mexican','brazil','brazilian','argentina','europe','european','britain','british','uk','ireland',
    'irish','france','french','germany','german','italy','spain','ukraine','ukrainian','russia','russian','china','chinese','japan',
    'india','indian','iran','iranian','israel','israeli','gaza','palestine','palestinian','iraq','syria','lebanon','turkey',
    'australia','australian','taiwan','korea','korean','africa','african','nato','united nations','brics'
}
US_DOMESTIC = US_STATES | {
    'chicago','detroit','indianapolis','houston','dallas','miami','atlanta','denver','phoenix','seattle','portland','boston',
    'philadelphia','baltimore','cleveland','milwaukee','minneapolis','st louis','kansas city','farmington','albuquerque'
}
SPORTS = {'nfl','football','basketball','baseball','hockey','soccer','ncaa','college football','bears','hoosiers','game','match'}
STRONG_SPORTS = {
    'nfl','football','college football','high school football','basketball','baseball','hockey','soccer','ncaa',
    'touchdown','quarterback','playoff','playoffs','score','scores','matchup','kickoff','roster','coach','coaching'
}
NFL_CONTEXT = {
    'nfl','national football league','super bowl','quarterback','touchdown','wide receiver','running back','tight end',
    'training camp','free agency'
}
CIVIC_CONTEXT = {
    'congress','senate','house of representatives','supreme court','court','judge','lawsuit','law','legislation','bill',
    'antitrust','title ix','government','governor','federal','department of justice','doj','investigation','regulation',
    'policy','civil rights','tax','taxpayer','public funding','stadium funding','ballot','election'
}
INTERNATIONAL_CONTEXT = {
    'war','military','troops','missile','airstrike','invasion','ceasefire','sanctions','diplomacy','diplomatic','summit',
    'prime minister','president','government','foreign minister','trade agreement','treaty','nato','united nations','brics'
}
TECH_SHOPPING = ('where to preorder','where to pre-order','preorder the','pre-order the','best deals','deal of the day','buy now','gift guide')
GAMING = {'gaming','video game','playstation','xbox','nintendo','switch','steam','skyrim','game mod','dlc','gamepass','game pass'}
GENERIC_LANDING = (
    re.compile(r'^all coverage\b', re.I), re.compile(r'^latest news\b', re.I), re.compile(r'^news$|^home$', re.I),
)

TOPIC_RULES = {
    'Health': ({'health','medical','medicine','disease','hospital','fda','doctor','public health','medicaid','medicare'}, {'world','us','federal','nm'}),
    'Technology & AI': ({'technology','artificial intelligence',' ai ','openai','google','apple','microsoft','cybersecurity','software','chip','semiconductor','data breach'}, {'technology'}),
    'Celebrities & Public Figures': ({'actor','actress','singer','rapper','musician','celebrity','star','athlete','director','artist'}, {'entertainment'}),
    'World': ({'international','world','war','diplomacy','summit','foreign','ukraine','russia','china','iran','israel','gaza','europe','brics'}, {'world','military'}),
    'Politics & Government': ({'white house','congress','senate','supreme court','president','election','government','federal','governor'}, {'presidential','federal','us'}),
    'Entertainment': ({'movie','film','television',' tv ','music','album','streaming','entertainment','actor','actress','singer'}, {'entertainment'}),
    'Sports': ({'nfl','nba','mlb','nhl','soccer','football','basketball','baseball','sports','athlete','game'}, {'nfl'}),
    'Business & Economy': ({'economy','business','stocks','market','tariff','jobs','company','companies','earnings','bank','inflation'}, {'us','world','federal'}),
    'Gaming': ({'gaming','video game','playstation','xbox','nintendo','steam','console','game studio','dlc'}, {'gaming'}),
    'Science': ({'science','research','study','nasa','space','climate','scientist','physics','biology','astronomy'}, {'world','us','technology'}),
}


def text(item, tag):
    return re.sub(r'\s+', ' ', item.findtext(tag) or '').strip()


def set_text(item, tag, value):
    node=item.find(tag)
    if node is None: node=ET.SubElement(item,tag)
    node.text=value


def tokens(value):
    return {w for w in re.findall(r'[a-z0-9]+', value.lower()) if len(w)>=3 and w not in STOP}


def phrases(value, terms):
    padded=' '+value.lower()+' '
    return {term for term in terms if (' '+term+' ' in padded if ' ' in term else re.search(r'\b'+re.escape(term)+r'\b', padded))}


def named_entities(value):
    chunks=re.findall(r'\b(?:[A-Z][a-zA-Z’\'-]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-zA-Z’\'-]+|[A-Z]{2,})){0,3}\b', value)
    noise={'The','This','That','News','Breaking','United States','White House','Associated Press'}
    return {c.lower() for c in chunks if c not in noise and len(c)>=4}


def related_enough(primary, related_title):
    a=tokens(text(primary,'title')); b=tokens(related_title)
    if not a or not b: return False
    shared=a&b
    if len(shared)>=4 and len(shared)/max(1,min(len(a),len(b)))>=0.55: return True
    entities=named_entities(text(primary,'title')) & named_entities(related_title)
    return bool(entities and len(shared)>=2)


def prune_related(item):
    rel=item.find('relatedArticles')
    if rel is None: return 0
    removed=0
    for article in list(rel.findall('article')):
        if not related_enough(item,text(article,'title')):
            rel.remove(article); removed+=1
    if not rel.findall('article'): item.remove(rel)
    return removed


def obvious_domestic_world(item):
    title=text(item,'title').lower(); desc=text(item,'description').lower(); full=f'{title} {desc}'
    foreign=phrases(full,FOREIGN)
    domestic=phrases(full,US_DOMESTIC)
    title_domestic=phrases(title,US_DOMESTIC)
    state_meta=text(item,'state').lower()
    sports=phrases(full,SPORTS)
    intl_context=phrases(full,INTERNATIONAL_CONTEXT)
    if title_domestic and not intl_context:
        return True
    if foreign:
        return False
    if state_meta and state_meta in US_STATES:
        return True
    return bool(domestic and sports)


def us_sports_disposition(item):
    """Return 'nfl', 'drop', or None for U.S.-tab sports leakage.

    Ordinary game/team/score coverage does not belong in the national U.S. news tab.
    NFL-specific stories can use the dedicated NFL tab. Sports stories whose central
    subject is government, law, courts, regulation, elections, public funding, etc.
    remain eligible for U.S./Federal coverage.
    """
    title=text(item,'title').lower(); desc=text(item,'description').lower(); full=f'{title} {desc}'
    sports=phrases(full,STRONG_SPORTS)
    if not sports:
        return None
    civic=phrases(full,CIVIC_CONTEXT)
    if civic:
        return None
    nfl=phrases(full,NFL_CONTEXT)
    if nfl:
        return 'nfl'
    return 'drop'


def x_relevant(item, topic):
    rules=TOPIC_RULES.get(topic)
    if not rules: return False
    terms,cats=rules
    full=' '+f"{text(item,'title')} {text(item,'description')}".lower()+' '
    cat=text(item,'category').lower()
    hits=sum(1 for term in terms if (term in full if ' ' in term else re.search(r'\b'+re.escape(term)+r'\b',full)))
    return hits>=1 and (cat=='x' or cat in cats)


def published(item):
    try: return parsedate_to_datetime(text(item,'pubDate')).astimezone(timezone.utc).timestamp()
    except Exception: return 0


def clone_x_from(candidate, topic):
    out=ET.Element('item')
    for tag in ('title','link','description','pubDate','source'):
        ET.SubElement(out,tag).text=text(candidate,tag)
    ET.SubElement(out,'category').text='x'
    ET.SubElement(out,'xTopic').text=topic
    ET.SubElement(out,'xSignal').text='Top public X conversation'
    ET.SubElement(out,'xWhyTrending').text='This fixed topic slot is populated by a current, independently reported story that matches the topic.'
    ET.SubElement(out,'xWhatPeopleAreSaying').text='People on X may discuss the issue from different perspectives; the trend signal does not make unverified claims factual.'
    ET.SubElement(out,'xConfirmed').text='Independent reporting confirms the underlying news event described above.'
    ET.SubElement(out,'xUnconfirmed').text='Rumors, screenshots, accusations, and interpretations circulating on X are not treated as facts unless independently verified.'
    return out


def repair_x(channel):
    items=list(channel.findall('item'))
    x_items=[i for i in items if text(i,'category').lower()=='x']
    base=[i for i in items if text(i,'category').lower() not in {'x','local','region','nm','legislation','boxoffice'}]
    by_topic={text(i,'xTopic'):i for i in x_items}
    used={text(i,'link') for i in x_items if text(i,'link')}
    repaired=0
    for topic in TOPIC_RULES:
        current=by_topic.get(topic)
        if current is not None and x_relevant(current,topic):
            continue
        candidates=[i for i in base if text(i,'link') not in used and x_relevant(i,topic)]
        if not candidates:
            raise SystemExit(f'Editorial integrity failed: no relevant replacement for X topic {topic}')
        replacement=clone_x_from(max(candidates,key=published),topic)
        used.add(text(replacement,'link'))
        if current is not None:
            idx=list(channel).index(current); channel.remove(current); channel.insert(idx,replacement)
        else:
            channel.append(replacement)
        repaired+=1
    all_x=[i for i in list(channel.findall('item')) if text(i,'category').lower()=='x']
    for i in all_x: channel.remove(i)
    final_by_topic={text(i,'xTopic'):i for i in all_x}
    for topic in TOPIC_RULES:
        item=final_by_topic.get(topic)
        if item is None or not x_relevant(item,topic):
            raise SystemExit(f'Editorial integrity failed: X topic {topic} is missing or irrelevant after repair')
        channel.append(item)
    return repaired


def main():
    tree=ET.parse(NEWS); channel=tree.getroot().find('channel')
    if channel is None: raise SystemExit('RSS channel not found')
    world_to_us=tech_to_gaming=us_to_nfl=us_sports_dropped=dropped=related_removed=0
    for item in list(channel.findall('item')):
        title=text(item,'title'); cat=text(item,'category').lower()
        if is_landing_page(item) or any(p.search(title) for p in GENERIC_LANDING):
            channel.remove(item); dropped+=1; continue
        if cat=='world' and obvious_domestic_world(item):
            set_text(item,'category','us'); world_to_us+=1
            cat='us'
        if cat=='us':
            sports_action=us_sports_disposition(item)
            if sports_action=='nfl':
                set_text(item,'category','nfl'); us_to_nfl+=1; cat='nfl'
            elif sports_action=='drop':
                channel.remove(item); us_sports_dropped+=1; continue
        if cat=='technology':
            low=title.lower(); full=f" {title} {text(item,'description')} ".lower()
            if any(term in low for term in TECH_SHOPPING):
                channel.remove(item); dropped+=1; continue
            if any(term in full for term in GAMING):
                set_text(item,'category','gaming'); tech_to_gaming+=1
        related_removed+=prune_related(item)
    repaired_x=repair_x(channel)
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Editorial integrity: World→US {world_to_us}; US→NFL {us_to_nfl}; US sports dropped {us_sports_dropped}; Technology→Gaming {tech_to_gaming}; dropped {dropped}; unrelated supporting links pruned {related_removed}; X slots repaired {repaired_x}.')

if __name__=='__main__': main()
