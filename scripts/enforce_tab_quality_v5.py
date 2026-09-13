#!/usr/bin/env python3
"""V5-only final tab-quality guard.

This layer is intentionally narrow and runs after the inherited V4 editorial guard.
It catches high-confidence residual leaks that are visible to readers without changing
V4 collection/ranking behavior: ordinary sports in general-news tabs, domestic
entertainment/crime in World, and low-value gaming review/guide pages.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

NEWS=Path('News')
REPORT=Path('tab-quality-report.json')

# Avoid generic nouns such as team/game/season: they create false sports matches in
# ordinary reporting (for example, "the White House team"). Use strong sport nouns,
# scorelines, or explicit competition verbs instead.
SPORTS_TERMS={
    'football','basketball','baseball','hockey','soccer','nfl','nba','mlb','nhl','ncaa',
    'touchdown','touchdowns','quarterback','overtime','triple-overtime','playoff','playoffs',
    'tournament','championship','standings','roster','kickoff','coach','coaches','league',
    'matchup','score','scores','scored',
}
SPORTS_VERBS={'beat','beats','defeat','defeats','defeated','wins','won','routs','routed','edges','edged','upsets','upset','rallies','rally'}
CIVIC_TERMS={
    'congress','senate','house of representatives','supreme court','court','judge','lawsuit','law',
    'legislation','bill','government','governor','federal','department of justice','doj','regulation',
    'policy','civil rights','tax','public funding','stadium funding','ballot','election','lobbyist',
    'city council','county commission','public money','antitrust','title ix',
}
NFL_TERMS={
    'nfl','national football league','super bowl','quarterback','touchdown','wide receiver','running back',
    'tight end','training camp','free agency','49ers','bengals','broncos','buccaneers','chargers','chiefs',
    'colts','commanders','dolphins','packers','patriots','ravens','seahawks','steelers','texans','titans',
    'arizona cardinals','atlanta falcons','baltimore ravens','buffalo bills','carolina panthers','chicago bears',
    'cincinnati bengals','cleveland browns','dallas cowboys','denver broncos','detroit lions','green bay packers',
    'houston texans','indianapolis colts','jacksonville jaguars','kansas city chiefs','las vegas raiders',
    'los angeles chargers','los angeles rams','miami dolphins','minnesota vikings','new england patriots',
    'new orleans saints','new york giants','new york jets','philadelphia eagles','pittsburgh steelers',
    'san francisco 49ers','seattle seahawks','tampa bay buccaneers','tennessee titans','washington commanders',
}
# Do not use generic words like "international" as evidence here. World descriptions
# are intentionally prefixed with "International reporting indicates", which previously
# made every World card look internationally scoped and hid domestic leakage.
WORLD_INTL={
    'nato','united nations','brics','international criminal court','icc','ukraine',
    'russia','china','iran','israel','gaza','palestine','west bank','europe','european union','africa','asia',
    'middle east','yemen','houthis','saudi','saudi arabia','iraq','syria','lebanon','taiwan','north korea',
    'south korea','india','pakistan','afghanistan','canada','mexico','brazil','argentina','france','germany',
    'britain','united kingdom','japan','australia','sanctions','diplomacy','diplomatic','war','ceasefire',
    'invasion','airstrike','missile','treaty','summit','foreign minister','prime minister',
}
US_FEDERAL={
    'cia','fbi','dhs','doj','department of justice','supreme court','congress','senate','white house',
    'u.s. government','us government','federal appeals court','federal court','federal agency',
}
US_DOMESTIC={
    'united states','u.s.','u.s ',' us ','american','9/11','september 11','cia','white house','congress',
    'supreme court','missouri','new york','california','texas','florida','illinois','indiana','ohio','iowa',
    'minnesota','wisconsin','arizona','colorado','new mexico','georgia','michigan','pennsylvania',
}
ENTERTAINMENT_TERMS={
    'actor','actress','singer','rapper','musician','celebrity','hollywood','grammy','oscar','album','movie','film',
    'television','tv','welcomes first child','pregnancy','fiancé','fiance','box office','concert','tour',
}
DOMESTIC_CRIME_TERMS={'murder-for-hire','murder','homicide','arrested','indicted','charged','trial','not guilty','guilty','police','prosecutors'}
LOW_VALUE_GAMING_PATTERNS=(
    re.compile(r'\breview\b',re.I),
    re.compile(r'\bwalkthrough\b',re.I),
    re.compile(r'\btier\s+list\b',re.I),
    re.compile(r'\bbest\s+.{0,35}\bgames?\b',re.I),
    re.compile(r'\bwhere\s+to\s+(?:buy|preorder|pre-order)\b',re.I),
    re.compile(r'\bcheats?\b',re.I),
    re.compile(r'\bgamefaqs\b',re.I),
)
NEWSWORTHY_GAMING={
    'announces','announced','launches','launched','release date','released','delayed','delay','acquires','acquired',
    'acquisition','lawsuit','sued','price increase','price hike','security breach','hack','outage','layoffs','layoff',
    'closes','closure','shuts down','shutdown','update','patch','expansion','dlc','trailer','showcase','blizzcon',
}


def clean(v): return re.sub(r'\s+',' ',v or '').strip()
def text(i,tag): return clean(i.findtext(tag))
def category(i): return text(i,'category').lower()
def set_category(i,value):
    n=i.find('category')
    if n is None:n=ET.SubElement(i,'category')
    n.text=value

def padded(i): return ' '+f"{text(i,'title')} {text(i,'description')}".lower()+' '
def has_term(full,term):
    if ' ' in term or '/' in term or '.' in term or '-' in term:return term in full
    return re.search(r'\b'+re.escape(term)+r'\b',full) is not None

def has_any(full,terms): return any(has_term(full,t) for t in terms)
def sports_story(i):
    full=padded(i); title=' '+text(i,'title').lower()+' '
    scoreline=bool(re.search(r'\b\d{1,3}\s*[-–]\s*\d{1,3}\b',title))
    return scoreline or has_any(full,SPORTS_TERMS) or has_any(title,SPORTS_VERBS)
def civic_story(i): return has_any(padded(i),CIVIC_TERMS)
def nfl_story(i): return has_any(padded(i),NFL_TERMS)
def international_story(i): return has_any(padded(i),WORLD_INTL)
def domestic_story(i): return has_any(padded(i),US_DOMESTIC)
def federal_story(i): return has_any(padded(i),US_FEDERAL)
def entertainment_story(i): return has_any(padded(i),ENTERTAINMENT_TERMS)
def domestic_crime_story(i): return domestic_story(i) and has_any(padded(i),DOMESTIC_CRIME_TERMS)

def low_value_gaming(i):
    title=text(i,'title'); full=padded(i); resolved=text(i,'resolvedPublisherUrl').lower()
    if has_any(full,NEWSWORTHY_GAMING): return False
    if '/reviews/' in resolved or '/review/' in resolved:return True
    return any(p.search(title) for p in LOW_VALUE_GAMING_PATTERNS)

def apply_rule(item):
    cat=category(item)
    if cat=='us' and sports_story(item) and not civic_story(item):
        return ('reroute','nfl','ordinary-sports-to-nfl') if nfl_story(item) else ('drop',None,'ordinary-sports-in-us')
    if cat=='world':
        intl=international_story(item)
        if sports_story(item) and not intl and not civic_story(item):
            return ('drop',None,'ordinary-sports-in-world')
        if entertainment_story(item) and not intl:
            return ('drop',None,'domestic-entertainment-in-world')
        if federal_story(item) and not intl:
            return ('reroute','federal','domestic-federal-in-world')
        if (domestic_story(item) or domestic_crime_story(item)) and not intl:
            return ('reroute','us','domestic-us-in-world')
    if cat=='gaming' and low_value_gaming(item):
        return ('drop',None,'gaming-review-guide-not-news')
    return ('keep',cat,'ok')

def run(feed=NEWS,report=REPORT,apply=True):
    tree=ET.parse(feed); channel=tree.getroot().find('channel')
    if channel is None:raise SystemExit('Invalid RSS: missing channel')
    items=list(channel.findall('item')); before=Counter(category(i) for i in items)
    actions=[]; removed=set()
    for idx,item in enumerate(items):
        original=category(item)
        action,dest,reason=apply_rule(item)
        if action=='reroute':set_category(item,dest)
        elif action=='drop':removed.add(idx)
        if action!='keep':actions.append({'title':text(item,'title'),'from':original,'action':action,'to':dest,'reason':reason})
    final=[i for idx,i in enumerate(items) if idx not in removed]
    after=Counter(category(i) for i in final)
    out={'generatedAt':datetime.now(timezone.utc).isoformat(),'inputArticles':len(items),'outputArticles':len(final),'removed':len(removed),'actions':actions,'categoryCountsBefore':dict(before),'categoryCountsAfter':dict(after),'policy':'high-confidence residual tab leak guard; V4 behavior otherwise preserved'}
    Path(report).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if actions:
        print('V5 tab-quality actions:')
        for a in actions:print(f" - {a['from']} {a['action']}->{a['to'] or '-'} [{a['reason']}]: {a['title']}")
    # A category may legitimately contain substantial contamination after a broad RSS pull.
    # Abort only if this conservative high-confidence pass would remove/reroute >35%.
    excessive={c:{'before':before[c],'after':after[c]} for c in ('world','us','gaming') if before[c]>=10 and after[c]<max(5,int(before[c]*.65))}
    if excessive:raise SystemExit('V5 tab-quality guard would over-prune: '+json.dumps(excessive,sort_keys=True))
    if apply:
        for i in list(channel.findall('item')):channel.remove(i)
        for i in final:channel.append(i)
        tree.write(feed,encoding='utf-8',xml_declaration=True)
    print(f"V5 tab quality: {len(items)} -> {len(final)}; {len(actions)} corrective action(s); {len(removed)} dropped")
    return out

if __name__=='__main__':run()
