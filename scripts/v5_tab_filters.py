#!/usr/bin/env python3
"""Fresh V5 per-tab semantic gates. Independent of all legacy classifiers."""
from __future__ import annotations
import re,xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict

CANONICAL_TABS=["top","nfl","x","underreported","world","us","presidential","federal","legislation","nm","local","region","technology","gaming","military","boxoffice"]
RANKING_SURFACES={"top","x"}
EDITORIAL_OVERLAYS={"underreported"}
PROTECTED_TABS={"boxoffice"}
OWNERSHIP_TABS=[x for x in CANONICAL_TABS if x not in RANKING_SURFACES|EDITORIAL_OVERLAYS|PROTECTED_TABS]
LEGACY_CATEGORY_MAP={"entertainment":"boxoffice"}
STOPWORDS=set("the a an and or but to of in on for with at by from as is are was were be been that this it its they them will would could may after before over under into about new news says report reports latest breaking".split())

TAB_TOPICS={
"top":"Highest-impact current stories across all qualified subject tabs; ranking surface, not exclusive ownership.",
"nfl":"NFL teams, players, games, league business, draft, injuries, standings and postseason. Excludes college/high-school football.",
"x":"Curated top issues/trending discussion surface; ranking surface, not exclusive ownership.",
"underreported":"Investigations, accountability, public records, public health, environment, rural/tribal impact and consequential stories receiving limited attention. Editorial overlay.",
"world":"International politics, society, economy, diplomacy, disasters and major foreign events that are not primarily military operations.",
"us":"National U.S. news, multi-state developments and domestic stories of national consequence that do not fit a more specific federal/presidential/legislation tab.",
"presidential":"President, White House, executive actions, administration policy and direct presidential political activity.",
"federal":"Congress, federal agencies, federal courts, DOJ/FBI/DHS/Treasury/IRS/EPA and federal governance. Excludes state institutions.",
"legislation":"Named bills, enacted laws, votes, vetoes, ordinances and formal rulemaking. Structured bill IDs get strongest ownership.",
"nm":"New Mexico statewide/state-level news and communities outside the immediate Four Corners local zone.",
"local":"Farmington/Four Corners immediate area: San Juan County, Aztec, Bloomfield, Kirtland, Shiprock, Durango, Cortez and nearby Navajo Nation communities.",
"region":"Broader Southwest/Four Corners region, primarily Arizona, Colorado and Utah, excluding stories that are specifically Local or NM.",
"technology":"Technology industry/products, AI, cybersecurity, semiconductors, software, devices, cloud, robotics and computing.",
"gaming":"Video games, consoles, PC gaming, studios, releases, gameplay, esports and gaming platforms. Excludes gambling/casino stories.",
"military":"Armed conflict, military operations, forces, weapons systems, strikes, deployments and defense operations. Excludes metaphorical 'war' and general veteran/community stories.",
"boxoffice":"Protected existing V5 Box Office behavior; excluded from the fresh ownership engine."
}

@dataclass(frozen=True)
class TabRule:
    positives:Dict[str,float]
    negatives:Dict[str,float]
    threshold:float
    specificity:int

def D(**kw):return {k.replace("u_s_","us_").replace("_"," "):v for k,v in kw.items()}
NFL_FRANCHISE={x:8 for x in ["arizona cardinals","atlanta falcons","baltimore ravens","buffalo bills","carolina panthers","chicago bears","cincinnati bengals","cleveland browns","dallas cowboys","denver broncos","detroit lions","green bay packers","houston texans","indianapolis colts","jacksonville jaguars","kansas city chiefs","las vegas raiders","los angeles chargers","los angeles rams","miami dolphins","minnesota vikings","new england patriots","new orleans saints","new york giants","new york jets","philadelphia eagles","pittsburgh steelers","san francisco 49ers","seattle seahawks","tampa bay buccaneers","tennessee titans","washington commanders"]}
NFL_ALIASES={x:7 for x in ["49ers","niners"]}

RULES={
"nfl":TabRule({**D(nfl=14,national_football_league=16,super_bowl=14,nfl_draft=13,nfl_playoffs=12,nfl_season=11,nfl_team=10,nfl_player=10),**NFL_FRANCHISE,**NFL_ALIASES},D(college_football=-25,high_school_football=-25,ncaaf=-25,ncaa=-18,soccer=-18,prep_football=-22),10,12),
"gaming":TabRule(D(video_game=13,gaming=11,playstation=12,ps5=11,xbox=12,nintendo=12,switch_2=12,nintendo_switch=11,steam=9,steam_deck=11,game_pass=10,game_studio=10,game_developer=10,game_development=9,game_publisher=9,epic_games=9,unreal_engine=9,console=8,pc_gaming=11,pc_gamer=10,gaming_handheld=9,esports=10,gameplay=8,dlc=7,game_release=9,release_date=7),D(casino=-20,gambling=-20,sportsbook=-20,lottery=-18,slot_machine=-18,tabletop=-25,board_game=-25,miniatures=-25,warhammer=-25,trading_card=-22,hobby_store=-20),9,11),
"technology":TabRule(D(artificial_intelligence=13,machine_learning=11,openai=13,chatgpt=13,anthropic=13,cybersecurity=12,cyberattack=12,data_breach=12,semiconductor=10,nvidia=10,amd=9,intel=9,cloud_computing=10,quantum_computing=11,robotics=9,smartphone=8,android=8,iphone=8,software=6,tech_industry=9,technology_company=8),D(virginia_tech=-25,louisiana_tech=-25,texas_tech=-25,georgia_tech=-25,technology_class=-12),9,10),
"military":TabRule(D(pentagon=14,armed_forces=13,troops=11,air_force=11,u_s_army=12,u_s_navy=12,army=7,navy=7,marines=11,military=8,defense=6,defense_budget=10,defense_chief=10,hegseth=9,missile=10,airstrike=12,air_strike=12,drone_strike=12,drone_warfare=10,underwater_drone=10,saildrone=10,usv=9,warfare=8,warship=11,combat=10,battlefield=11,invasion=11,ceasefire=9,defense_department=14,centcom=14,military_operation=13,military_strike=13,military_deployment=12,military_aircraft=11,military_equipment=11,munition=10,munitions=10,weapon_system=10,fighter_jet=10,f_35=10,apache=9,anduril=9,warfighter=9,warfighters=9,attacks_on_shipping=10),D(border_war=-24,war_on_drugs=-22,price_war=-22,trade_war=-20,culture_war=-20,war_against=-18,veterans_museum=-18,veterans_day=-16,military_veteran=-10,war_memorial=-16,defense_attorney=-20,defense_lawyer=-20,team_defense=-14,defense_production_act=-20,food_bank=-20,food_giveaway=-20,enlistment=-12),10,11),
"presidential":TabRule(D(president_trump=14,donald_trump=11,trump_administration=14,white_house=13,executive_order=13,oval_office=12,press_secretary=10,presidential=9,commander_in_chief=10,administration_policy=8),D(former_president=-7,company_president=-20,university_president=-20,team_president=-20),10,10),
"legislation":TabRule(D(legislation=13,signed_into_law=15,statute=11,ordinance=11,final_rule=11,rulemaking=11,house_passed=11,senate_passed=11,passed_the_house=11,passed_the_senate=11,veto=10,enacted=11,law_takes_effect=12,bill=5,bipartisan_bill=8),D(lawsuit=-12,law_firm=-16,law_enforcement=-12,billboard=-20),10,13),
"federal":TabRule(D(u_s_congress=13,congress=10,u_s_senate=12,house_of_representatives=12,u_s_supreme_court=14,scotus=14,department_of_justice=13,doj=11,fbi=11,dhs=11,u_s_treasury=11,treasury_department=11,epa=10,irs=10,federal_court=12,federal_appeals_court=13,federal_judge=12,federal_agency=11,federal_government=10,federal_debt=10,senate_hearing=10),D(federal_credit_union=-25,state_supreme_court=-25,state_senate=-22,state_house=-22,state_legislature=-22),10,9),
"local":TabRule(D(farmington=17,san_juan_county=17,aztec=15,bloomfield=15,kirtland=14,shiprock=15,four_corners=16,durango=14,la_plata_county=15,cortez=14,montezuma_county=15,navajo_nation=13,farmington_police=18,farmington_municipal=18,san_juan_regional=17),{},11,14),
"nm":TabRule(D(new_mexico=15,new_mexicans=12,santa_fe=10,albuquerque=10,las_cruces=10,rio_rancho=10,new_mexico_legislature=17,new_mexico_governor=16,nmdot=14),{},10,12),
"region":TabRule(D(arizona=9,colorado=9,utah=9,four_corners_region=13,flagstaff=10,phoenix=8,denver=8,salt_lake_city=8,southern_colorado=11,northern_arizona=11),D(california=-14,texas=-14,oregon=-14,washington_state=-14,new_hampshire=-22,college_football=-14,high_school_football=-14),9,8),
"world":TabRule(D(ukraine=8,russia=8,china=7,iran=8,israel=8,gaza=8,france=7,germany=7,united_kingdom=7,japan=7,india=7,canada=7,mexico=7,afghanistan=8,saudi=8,taiwan=8,nato=9,united_nations=9,diplomacy=9,diplomatic=9,international=6,foreign_minister=8,prime_minister=7),D(new_mexico=-24),7,5),
"us":TabRule(D(united_states=9,america=7,american=6,americans=6,nationwide=9,across_the_country=9,nationally=8,multi_state=9),D(high_school=-8,local_team=-8),7,4),
"underreported":TabRule(D(public_records=10,accountability=9,whistleblower=12,oversight=9,audit=8,investigation=7,investigative=9,medicare=8,medicaid=8,public_health=8,pollution=7,contamination=9,toxic=8,rural=6,tribal=7,voting_rules=8,disenfranchisement=9,patient_records=8,water_crisis=7,environmental_justice=8,regulatory_failure=9,government_watchdog=10),D(celebrity=-16,box_office=-16,sports=-11,horoscope=-20),7,3),
"boxoffice":TabRule({}, {},999,0),
"x":TabRule({}, {},0,1),"top":TabRule({}, {},0,0)}

def field(i:ET.Element,n:str)->str:return (i.findtext(n) or "").strip()
def clean_title(i:ET.Element)->str:
    t=field(i,"title");p=t.rsplit(" - ",1)
    if len(p)==2 and 2<=len(p[1].split())<=10:t=p[0]
    return t
def norm(s:str)->str:
    s=(s or "").lower().replace("u.s.","us").replace("u.s ","us ")
    return " "+re.sub(r"\s+"," ",s).strip()+" "
def parts(i):return norm(clean_title(i)),norm(field(i,"description")),norm(field(i,"whyMatters"))
def has(text,phrase):
    p=phrase.lower();return p in text if (" " in p or "." in p or "-" in p) else re.search(rf"\b{re.escape(p)}\b",text) is not None

def legislation_id(i):
    m=re.search(r"\b(H\.R\.|HR|S\.|HB|SB)\s*-?\s*(\d+)\b",clean_title(i).upper());return (m.group(1).replace(".","")+m.group(2)) if m else ""
def is_legislation(i):return bool(legislation_id(i) or re.search(r"\b\d{3}(?:st|nd|rd|th) Congress\b",clean_title(i),re.I))
def obvious_noise(i):
    t=norm(clean_title(i));return any(x in t for x in [" obituary "," winning numbers "," lottery "," things to do "," classifieds "," job postings "," horoscope "," recipe "," prep roundup "," latest defense news weekly videos "," latest - defense news "," author "," current & breaking news "," odds, picks and predictions ",".jpg "])

def raw(i,tab):
    r=RULES[tab];title,desc,why=parts(i);full=title+desc+why;s=30. if tab=="legislation" and is_legislation(i) else 0.;ev=[]
    source_title=norm(field(i,"title"))
    source_bonus=10 if tab=="gaming" and has(source_title,"pc gamer") else 0
    if source_bonus:s+=source_bonus;ev.append("+source:pc gamer")
    for term,w in r.positives.items():
        if has(full,term):s+=w;ev.append("+"+term)
        if has(title,term):s+=w*2;ev.append("+title:"+term)
    for term,w in r.negatives.items():
        if has(full,term):s+=w;ev.append("!"+term)
    title_strength=sum(w for term,w in r.positives.items() if has(title,term))+source_bonus
    if tab in {"nfl","presidential","technology","gaming"} and title_strength==0:s=min(s,r.threshold-0.1)
    return round(s,2),ev

def score_tab_raw(i,tab):return raw(i,tab)[0]
def score_tab(i,tab):
    s,ev=raw(i,tab)
    if tab=="nm" and score_tab_raw(i,"local")>=RULES["local"].threshold:s-=10;ev.append("!local-specific")
    if tab=="region" and (score_tab_raw(i,"local")>=RULES["local"].threshold or score_tab_raw(i,"nm")>=RULES["nm"].threshold):s-=10;ev.append("!more-specific-geography")
    if tab in {"world","us"}:
        for x in ["military","technology","gaming","nfl","presidential","federal","legislation"]:
            if score_tab_raw(i,x)>=RULES[x].threshold+2:s-=7;ev.append("!specific:"+x)
    return round(s,2),ev

def all_scores(i):return {t:score_tab(i,t)[0] for t in CANONICAL_TABS}
def qualifies(i,tab):return tab in RANKING_SURFACES or tab in PROTECTED_TABS or score_tab(i,tab)[0]>=RULES[tab].threshold

def best_tab(i,include_underreported=True):
    scores=all_scores(i)
    if is_legislation(i):return "legislation",scores["legislation"],scores
    ok=[t for t in OWNERSHIP_TABS if scores[t]>=RULES[t].threshold]
    if not ok:return None,0.,scores
    ok.sort(key=lambda t:(RULES[t].specificity,scores[t]-RULES[t].threshold,scores[t]),reverse=True);w=ok[0];return w,scores[w],scores

def tab_filter_decision(i):
    rawcat=field(i,"category").lower();cur=LEGACY_CATEGORY_MAP.get(rawcat,rawcat)
    if cur in RANKING_SURFACES:return {"action":"keep","current":cur,"target":cur,"reason":"ranking-surface","scores":all_scores(i)}
    if cur in PROTECTED_TABS:return {"action":"keep","current":cur,"target":cur,"reason":"protected-tab","scores":all_scores(i)}
    if obvious_noise(i):return {"action":"reject","current":cur,"target":None,"reason":"global-noise","scores":all_scores(i)}
    if cur in EDITORIAL_OVERLAYS:return {"action":"keep","current":cur,"target":cur,"reason":"editorial-overlay-preserved","scores":all_scores(i)}
    w,_,scores=best_tab(i)
    if not w:return {"action":"reject","current":cur,"target":None,"reason":"no-qualified-tab","scores":scores}
    if cur in {"local","region"} and w in {"us","world"} and scores[w]<RULES[w].threshold+6:
        return {"action":"reject","current":cur,"target":None,"reason":"out-of-area-local-sweep","scores":scores}
    if cur==w and qualifies(i,cur):return {"action":"keep","current":cur,"target":w,"reason":"tab-qualified","scores":scores}
    return {"action":"reroute","current":cur,"target":w,"reason":"stronger-tab:"+w,"scores":scores}

def content_tokens(i):
    title,desc,_=parts(i);return {t for t in re.findall(r"[a-z0-9]+",title+desc) if len(t)>=3 and t not in STOPWORDS}
