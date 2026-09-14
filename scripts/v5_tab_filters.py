#!/usr/bin/env python3
"""Fresh V5 per-tab semantic gates. Independent of all legacy classifiers."""
from __future__ import annotations
import re,xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict,List,Tuple
CANONICAL_TABS=["top","nfl","x","underreported","world","us","presidential","federal","legislation","nm","local","region","technology","gaming","military","boxoffice"]
RANKING_SURFACES={"top","x"}
OWNERSHIP_TABS=[x for x in CANONICAL_TABS if x not in RANKING_SURFACES]
LEGACY_CATEGORY_MAP={"entertainment":"boxoffice"}
STOPWORDS=set("the a an and or but to of in on for with at by from as is are was were be been that this it its they them will would could may after before over under into about new news says report reports latest breaking".split())
@dataclass(frozen=True)
class TabRule: positives:Dict[str,float];negatives:Dict[str,float];threshold:float;specificity:int

def D(**kw):return {k.replace("_"," "):v for k,v in kw.items()}
NFL_FRANCHISE={x:7 for x in ["arizona cardinals","atlanta falcons","baltimore ravens","buffalo bills","carolina panthers","chicago bears","cincinnati bengals","cleveland browns","dallas cowboys","denver broncos","detroit lions","green bay packers","houston texans","indianapolis colts","jacksonville jaguars","kansas city chiefs","las vegas raiders","los angeles chargers","los angeles rams","miami dolphins","minnesota vikings","new england patriots","new orleans saints","new york giants","new york jets","philadelphia eagles","pittsburgh steelers","san francisco 49ers","seattle seahawks","tampa bay buccaneers","tennessee titans","washington commanders"]}
RULES={
"nfl":TabRule({**D(nfl=12,national_football_league=14,super_bowl=12,nfl_draft=10,nfl_playoffs=10,nfl_season=9),**NFL_FRANCHISE},D(college_football=-20,high_school_football=-20,ncaaf=-20),9,10),
"gaming":TabRule(D(video_game=11,gaming=10,playstation=11,xbox=11,nintendo=11,steam=8,game_studio=9,console=7,pc_gaming=10,esports=9,gameplay=7,dlc=6),D(casino=-16,gambling=-16,sportsbook=-16,lottery=-14),8,10),
"technology":TabRule(D(artificial_intelligence=12,machine_learning=10,openai=12,chatgpt=12,anthropic=12,cybersecurity=11,cyberattack=11,data_breach=11,semiconductor=9,nvidia=9,amd=8,intel=8,cloud_computing=9,quantum_computing=10,robotics=8,smartphone=7,android=7,iphone=7,software=5,technology=5),D(virginia_tech=-20,louisiana_tech=-20,texas_tech=-20,georgia_tech=-20),8,9),
"military":TabRule(D(pentagon=12,armed_forces=11,troops=9,air_force=9,u_s_army=10,u_s_navy=10,marines=9,missile=8,airstrike=10,air_strike=10,drone_strike=10,warship=10,combat=8,battlefield=9,invasion=9,ceasefire=7,defense_department=12,centcom=12,military_operation=11,military_strike=11,weapon=5,weapons=5),D(border_war=-20,war_on_drugs=-18,price_war=-18,trade_war=-16,culture_war=-16,war_against=-14,veterans_museum=-12),9,9),
"presidential":TabRule(D(president_trump=13,donald_trump=12,white_house=11,executive_order=11,oval_office=11,press_secretary=8,presidential=8,commander_in_chief=9),D(former_president=-5,company_president=-16,university_president=-16,team_president=-16),9,9),
"legislation":TabRule(D(legislation=11,signed_into_law=13,lawmakers=6,statute=9,ordinance=10,final_rule=9,rulemaking=9,house_passed=9,senate_passed=9,veto=8,enacted=9,law_takes_effect=10,bill=6),D(lawsuit=-8,law_firm=-12,law_enforcement=-8),9,10),
"federal":TabRule(D(u_s_congress=11,congress=8,u_s_senate=10,house_of_representatives=10,u_s_supreme_court=12,scotus=12,department_of_justice=11,doj=9,fbi=9,dhs=9,u_s_treasury=9,treasury_department=9,epa=8,irs=8,federal_court=10,federal_judge=10,federal_agency=9),D(federal_credit_union=-20,state_supreme_court=-14),9,8),
"local":TabRule(D(farmington=15,san_juan_county=15,aztec=13,bloomfield=13,kirtland=12,shiprock=13,four_corners=14,durango=12,la_plata_county=13,cortez=12,montezuma_county=13,navajo_nation=12,gallup=10,farmington_police=16,farmington_municipal=16,san_juan_regional=15),{},10,12),
"nm":TabRule(D(new_mexico=14,santa_fe=9,albuquerque=9,las_cruces=9,rio_rancho=9,new_mexico_legislature=15,new_mexico_governor=14,nmdot=12),{},10,10),
"region":TabRule(D(arizona=8,colorado=8,utah=8,southwest=9,four_corners_region=11,flagstaff=8,phoenix=7,denver=7,salt_lake_city=7,southern_colorado=9,northern_arizona=9),D(california=-12,texas=-12,oregon=-12,washington_state=-12,new_hampshire=-20),8,7),
"world":TabRule(D(ukraine=7,russia=7,china=6,iran=7,israel=7,gaza=7,france=6,germany=6,united_kingdom=6,japan=6,india=6,canada=6,mexico=6,afghanistan=7,saudi=7,taiwan=7,nato=8,united_nations=8,diplomacy=7,diplomatic=7),{},7,4),
"us":TabRule(D(united_states=8,u_s=8,nationwide=7,across_the_country=7,americans=5,american=4),{},7,3),
"underreported":TabRule(D(public_records=9,accountability=8,whistleblower=11,oversight=8,audit=7,investigation=6,medicare=7,medicaid=7,hospital=5,public_health=7,pollution=6,contamination=8,toxic=7,rural=5,tribal=6,voting_rules=7,disenfranchisement=8,abortion_ban=7,abortion_bans=7,patient_records=7,water_crisis=6),D(celebrity=-14,box_office=-14,sports=-9),7,2),
"boxoffice":TabRule(D(box_office=13,opening_weekend=11,weekend_gross=12,domestic_gross=12,worldwide_gross=11,theatrical=8,imax=8,ticket_sales=9,movie_release=7,film_release=7),D(movie_theater_shooting=-14,home_theater=-14),9,9),
"x":TabRule({}, {},0,1),"top":TabRule({}, {},0,0)}

def field(i:ET.Element,n:str)->str:return (i.findtext(n) or "").strip()
def clean_title(i:ET.Element)->str:
    t=field(i,"title");parts=t.rsplit(" - ",1)
    if len(parts)==2 and 2<=len(parts[1].split())<=10:t=parts[0]
    return t
def norm(s:str)->str:return " "+re.sub(r"\s+"," ",(s or "").lower()).strip()+" "
def parts(i):return norm(clean_title(i)),norm(field(i,"description")),norm(field(i,"whyMatters"))
def has(text,phrase):
    p=phrase.lower();return p in text if (" " in p or "." in p or "-" in p) else re.search(rf"\b{re.escape(p)}\b",text) is not None

def legislation_id(i):
    m=re.search(r"\b(H\.R\.|HR|S\.|HB|SB)\s*-?\s*(\d+)\b",clean_title(i).upper());return (m.group(1).replace(".","")+m.group(2)) if m else ""
def is_legislation(i):return bool(legislation_id(i) or re.search(r"\b\d{3}(?:st|nd|rd|th) Congress\b",clean_title(i),re.I))
def obvious_noise(i):
    t=norm(clean_title(i));return any(x in t for x in [" obituary "," winning numbers "," lottery "," things to do "," classifieds "," job postings "," horoscope "," recipe "," prep roundup "])

def raw(i,tab):
    r=RULES[tab];title,desc,why=parts(i);full=title+desc+why;s=30. if tab=="legislation" and is_legislation(i) else 0.;ev=[]
    for term,w in r.positives.items():
        if has(full,term):s+=w;ev.append("+"+term)
        if has(title,term):s+=w*2;ev.append("+title:"+term)
    for term,w in r.negatives.items():
        if has(full,term):s+=w;ev.append("!"+term)
    if tab in {"nfl","presidential","military","technology","gaming"}:
        title_strength=sum(w for term,w in r.positives.items() if has(title,term))
        if title_strength==0 and s<r.threshold+7:s=min(s,r.threshold-0.1)
    return round(s,2),ev
def score_tab_raw(i,tab):return raw(i,tab)[0]
def score_tab(i,tab):
    s,ev=raw(i,tab)
    if tab=="nm" and score_tab_raw(i,"local")>=RULES["local"].threshold:s-=9;ev.append("!local-specific")
    if tab=="region" and (score_tab_raw(i,"local")>=RULES["local"].threshold or score_tab_raw(i,"nm")>=RULES["nm"].threshold):s-=9;ev.append("!more-specific-geography")
    if tab in {"world","us"}:
        for x in ["military","technology","gaming","nfl","presidential","federal","legislation"]:
            if score_tab_raw(i,x)>=RULES[x].threshold+4:s-=5;ev.append("!specific:"+x)
    return round(s,2),ev
def all_scores(i):return {t:score_tab(i,t)[0] for t in CANONICAL_TABS}
def qualifies(i,tab):return tab in RANKING_SURFACES or score_tab(i,tab)[0]>=RULES[tab].threshold
def best_tab(i,include_underreported=True):
    scores=all_scores(i);c=[t for t in OWNERSHIP_TABS if include_underreported or t!="underreported"];ok=[t for t in c if scores[t]>=RULES[t].threshold]
    if not ok:return None,0.,scores
    ok.sort(key=lambda t:((scores[t]-RULES[t].threshold)+RULES[t].specificity*.7,scores[t]),reverse=True);w=ok[0];return w,scores[w],scores
def tab_filter_decision(i):
    rawcat=field(i,"category").lower();cur=LEGACY_CATEGORY_MAP.get(rawcat,rawcat)
    if cur in RANKING_SURFACES:return {"action":"keep","current":cur,"target":cur,"reason":"ranking-surface","scores":all_scores(i)}
    if obvious_noise(i):return {"action":"reject","current":cur,"target":None,"reason":"global-noise","scores":all_scores(i)}
    w,_,scores=best_tab(i,include_underreported=(cur=="underreported"))
    if not w:return {"action":"reject","current":cur,"target":None,"reason":"no-qualified-tab","scores":scores}
    if cur in {"local","region"} and w in {"us","world"} and scores[w]<RULES[w].threshold+6:return {"action":"reject","current":cur,"target":None,"reason":"out-of-area-local-sweep","scores":scores}
    if cur==w and qualifies(i,cur):return {"action":"keep","current":cur,"target":w,"reason":"tab-qualified","scores":scores}
    return {"action":"reroute","current":cur,"target":w,"reason":"stronger-tab:"+w,"scores":scores}
def content_tokens(i):
    title,desc,_=parts(i);return {t for t in re.findall(r"[a-z0-9]+",title+desc) if len(t)>=3 and t not in STOPWORDS}
