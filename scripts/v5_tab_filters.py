#!/usr/bin/env python3
"""Fresh V5 per-tab relevance and ownership rules. No legacy classifier imports."""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict,Iterable,List,Tuple

CANONICAL_TABS=["top","nfl","x","underreported","world","us","presidential","federal","legislation","nm","local","region","technology","gaming","military","boxoffice"]
RANKING_SURFACES={"top","x"}
OWNERSHIP_TABS=["nfl","underreported","world","us","presidential","federal","legislation","nm","local","region","technology","gaming","military","boxoffice"]
LEGACY_CATEGORY_MAP={"entertainment":"boxoffice"}
STOPWORDS={"the","a","an","and","or","but","to","of","in","on","for","with","at","by","from","as","is","are","was","were","be","been","that","this","it","its","they","them","will","would","could","may","after","before","over","under","into","about","new","news","says","report","reports","latest","breaking"}

@dataclass(frozen=True)
class TabRule:
    positives:Dict[str,float]; negatives:Dict[str,float]; threshold:float; title_bonus:float=2.0; specificity:int=1

def _d(x:Iterable[Tuple[str,float]])->Dict[str,float]: return dict(x)
NFL_TEAMS=["cardinals","falcons","ravens","bills","panthers","bears","bengals","browns","cowboys","broncos","lions","packers","texans","colts","jaguars","chiefs","raiders","chargers","rams","dolphins","vikings","patriots","saints","giants","jets","eagles","steelers","49ers","seahawks","buccaneers","titans","commanders"]
RULES={
"nfl":TabRule(_d([("nfl",10),("national football league",12),("super bowl",10),("nfc",7),("afc",7),("touchdown",4),("quarterback",4),("free agency",6),("training camp",6),("roster",4)]+[(x,4) for x in NFL_TEAMS]),_d([("college football",-16),("ncaaf",-16),("high school football",-16),("soccer",-12),("fifa",-12)]),8,specificity=10),
"gaming":TabRule(_d([("video game",10),("gaming",9),("playstation",10),("xbox",10),("nintendo",10),("steam",7),("game studio",8),("console",6),("pc gaming",9),("esports",8),("gameplay",7),("dlc",6),("geforce",5),("radeon",5)]),_d([("casino",-14),("gambling",-14),("sportsbook",-14),("lottery",-12)]),7,specificity=10),
"technology":TabRule(_d([("technology",5),("artificial intelligence",10),("machine learning",9),("openai",10),("chatgpt",10),("anthropic",10),("cybersecurity",10),("cyberattack",10),("data breach",10),("software",5),("semiconductor",8),("nvidia",8),("amd",7),("intel",7),("microsoft",5),("google",5),("apple",5),("cloud computing",8),("robotics",7),("quantum computing",9),("smartphone",6),("android",6),("iphone",6)]),_d([("virginia tech",-20),("louisiana tech",-20),("texas tech",-20),("georgia tech",-20),("touchdown",-10),("nfl",-10)]),7,specificity=9),
"military":TabRule(_d([("pentagon",11),("armed forces",10),("troops",8),("air force",8),("u.s. army",9),("u.s. navy",9),("marines",8),("missile",7),("airstrike",9),("air strike",9),("drone strike",9),("warship",9),("combat",7),("battlefield",8),("invasion",8),("ceasefire",6),("defense department",11),("centcom",11),("military operation",10),("military strike",10),("military",6)]),_d([("border war",-20),("war on drugs",-16),("price war",-16),("trade war",-14),("culture war",-14),("war against",-12),("veterans museum",-10),("veteran food",-10)]),8,specificity=9),
"presidential":TabRule(_d([("president trump",12),("donald trump",11),("white house",10),("executive order",10),("oval office",10),("press secretary",7),("presidential",8),("commander in chief",8)]),_d([("former president",-5),("company president",-14),("university president",-14),("team president",-14)]),8,specificity=9),
"legislation":TabRule(_d([("legislation",10),("signed into law",12),("lawmakers",5),("statute",8),("ordinance",9),("final rule",8),("rulemaking",8),("house passed",8),("senate passed",8),("veto",7),("enacted",8),("law takes effect",9),("bill",6)]),_d([("lawsuit",-7),("law firm",-10),("law enforcement",-7)]),8,specificity=10),
"federal":TabRule(_d([("u.s. congress",10),("congress",7),("u.s. senate",9),("house of representatives",9),("u.s. supreme court",11),("scotus",11),("department of justice",10),("doj",8),("fbi",8),("dhs",8),("u.s. treasury",8),("treasury department",8),("epa",7),("sec",6),("fcc",6),("irs",7),("federal court",9),("federal judge",9),("federal agency",8)]),_d([("federal credit union",-18),("state supreme court",-12)]),8,specificity=8),
"local":TabRule(_d([("farmington",14),("san juan county",14),("aztec",12),("bloomfield",12),("kirtland",11),("shiprock",12),("four corners",13),("durango",11),("la plata county",12),("cortez",11),("montezuma county",12),("navajo nation",11),("gallup",9),("farmington police",15),("farmington municipal",15),("san juan regional",14)]),_d([]),9,specificity=12),
"nm":TabRule(_d([("new mexico",13),("santa fe",8),("albuquerque",8),("las cruces",8),("rio rancho",8),("new mexico legislature",14),("new mexico governor",13),("nmdot",11)]),_d([]),9,specificity=10),
"region":TabRule(_d([("arizona",7),("colorado",7),("utah",7),("southwest",8),("four corners region",10),("flagstaff",7),("phoenix",6),("denver",6),("salt lake city",6),("southern colorado",8),("northern arizona",8)]),_d([("new hampshire",-20),("oregon",-12),("washington state",-12),("california",-10),("texas",-10)]),7,specificity=7),
"world":TabRule(_d([("international",5),("diplomatic",6),("diplomacy",6),("united nations",8),("nato",7),("ukraine",6),("russia",6),("china",5),("iran",6),("israel",6),("gaza",6),("france",5),("germany",5),("united kingdom",5),("japan",5),("india",5),("canada",5),("mexico",5),("afghanistan",6),("saudi",6),("taiwan",6)]),_d([("nfl",-10),("super bowl",-10)]),6,specificity=4),
"us":TabRule(_d([("united states",7),("u.s.",7),("american",4),("americans",4),("nationwide",6),("across the country",6),("governor",4),("state officials",5),("state law",5)]),_d([("nfl",-8),("playstation",-8),("xbox",-8)]),6,specificity=3),
"underreported":TabRule(_d([("public records",9),("accountability",8),("whistleblower",10),("oversight",7),("audit finds",8),("investigation finds",8),("tribal",5),("rural",5),("contamination",7),("toxic",6),("neglected",6)]),_d([("celebrity",-12),("box office",-12),("sports",-8)]),7,specificity=2),
"boxoffice":TabRule(_d([("box office",12),("opening weekend",10),("weekend gross",11),("domestic gross",11),("worldwide gross",10),("theatrical",7),("imax",7),("ticket sales",8),("movie release",6),("film release",6)]),_d([("movie theater shooting",-12),("home theater",-12)]),8,specificity=9),
"x":TabRule(_d([("election",4),("immigration",4),("economy",4),("inflation",4),("war",4),("abortion",4),("healthcare",4),("supreme court",4),("congress",4),("trump",4),("climate",4),("border",4),("tariff",4)]),_d([]),4,specificity=1),
"top":TabRule({}, {},0,specificity=0),
}
US_STATES={"alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi","missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico","new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania","rhode island","south carolina","south dakota","tennessee","texas","utah","vermont","virginia","washington","west virginia","wisconsin","wyoming"}

def normalize(s:str)->str:return " "+re.sub(r"\s+"," ",(s or "").lower()).strip()+" "
def field(item:ET.Element,name:str)->str:return (item.findtext(name) or "").strip()
def text_parts(item:ET.Element)->Tuple[str,str,str]:return normalize(field(item,"title")),normalize(field(item,"description")),normalize(field(item,"whyMatters"))
def phrase_present(text:str,phrase:str)->bool:
    p=phrase.lower().strip()
    if not p:return False
    if " " in p or "." in p or "-" in p:return p in text
    return re.search(rf"\b{re.escape(p)}\b",text) is not None

def legislation_id(item:ET.Element)->str:
    t=field(item,"title").upper().replace("—","-")
    m=re.search(r"\b(H\.R\.|HR|S\.|HB|SB)\s*-?\s*(\d+)\b",t)
    return (m.group(1).replace(".","")+m.group(2)) if m else ""
def is_legislation(item:ET.Element)->bool:
    t=field(item,"title")
    return bool(legislation_id(item) or re.search(r"\b\d{3}(?:st|nd|rd|th) Congress\b",t,re.I))
def obvious_noise(item:ET.Element)->bool:
    t=normalize(field(item,"title"))
    bad=[" obituary "," winning numbers "," lottery "," things to do "," classifieds "," job postings "," horoscope "," recipe "," prep roundup "]
    return any(x in t for x in bad)

def _base_score(item:ET.Element,tab:str)->Tuple[float,List[str]]:
    rule=RULES[tab];title,desc,why=text_parts(item); full=title+desc+why;score=0.;ev=[]
    if tab=="legislation" and is_legislation(item):score+=30;ev.append("+structured-bill-id")
    for term,w in rule.positives.items():
        if phrase_present(full,term):
            score+=w;ev.append("+"+term)
            if phrase_present(title,term):score+=w*rule.title_bonus;ev.append("+title:"+term)
    for term,w in rule.negatives.items():
        if phrase_present(full,term):score+=w;ev.append("!"+term)
    if tab=="us" and any(phrase_present(title,s) for s in US_STATES):score+=3;ev.append("+title-us-state")
    return score,ev

def score_tab_raw(item:ET.Element,tab:str)->float:return round(_base_score(item,tab)[0],2)
def score_tab(item:ET.Element,tab:str)->Tuple[float,List[str]]:
    score,ev=_base_score(item,tab)
    if tab=="nm" and score_tab_raw(item,"local")>=RULES["local"].threshold:score-=8;ev.append("!local-specific")
    if tab=="region" and (score_tab_raw(item,"local")>=RULES["local"].threshold or score_tab_raw(item,"nm")>=RULES["nm"].threshold):score-=8;ev.append("!more-specific-geography")
    if tab in {"world","us"}:
        for s in ("military","technology","gaming","nfl","presidential","federal","legislation"):
            if score_tab_raw(item,s)>=RULES[s].threshold+3:score-=5;ev.append("!specific:"+s)
    return round(score,2),ev
def all_scores(item:ET.Element)->Dict[str,float]:return {t:score_tab(item,t)[0] for t in CANONICAL_TABS}
def qualifies(item:ET.Element,tab:str)->bool:
    if tab in RANKING_SURFACES:return True
    return score_tab(item,tab)[0]>=RULES[tab].threshold

def best_tab(item:ET.Element,include_underreported:bool=True)->Tuple[str|None,float,Dict[str,float]]:
    scores=all_scores(item);cands=list(OWNERSHIP_TABS)
    if not include_underreported:cands.remove("underreported")
    eligible=[t for t in cands if scores[t]>=RULES[t].threshold]
    if not eligible:return None,0.,scores
    eligible.sort(key=lambda t:(scores[t]-RULES[t].threshold,RULES[t].specificity,scores[t]),reverse=True)
    winner=eligible[0]
    if len(eligible)>1:
        a= scores[winner]-RULES[winner].threshold; b=scores[eligible[1]]-RULES[eligible[1]].threshold
        if a-b<1.5 and RULES[winner].specificity<RULES[eligible[1]].specificity:winner=eligible[1]
    return winner,scores[winner],scores

def tab_filter_decision(item:ET.Element)->dict:
    current=LEGACY_CATEGORY_MAP.get(field(item,"category").lower(),field(item,"category").lower())
    if current in RANKING_SURFACES:return {"action":"keep","current":current,"target":current,"reason":"ranking-surface","scores":all_scores(item)}
    if obvious_noise(item):return {"action":"reject","current":current,"target":None,"reason":"global-noise","scores":all_scores(item)}
    winner,score,scores=best_tab(item,include_underreported=(current=="underreported"))
    if winner is None:return {"action":"reject","current":current,"target":None,"reason":"no-qualified-tab","scores":scores}
    if current==winner and qualifies(item,current):return {"action":"keep","current":current,"target":winner,"reason":"tab-qualified","scores":scores}
    return {"action":"reroute","current":current,"target":winner,"reason":f"stronger-tab:{winner}","scores":scores}

def content_tokens(item:ET.Element)->set[str]:
    title,desc,_=text_parts(item);return {t for t in re.findall(r"[a-z0-9]+",title+desc) if len(t)>=3 and t not in STOPWORDS}
