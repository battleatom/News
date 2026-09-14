#!/usr/bin/env python3
"""Fresh V5 per-tab relevance filters.

This module is intentionally self-contained and does not import legacy classifiers.
It scores each article against every canonical tab using positive evidence,
negative/exclusion evidence, geography, and central-subject specificity.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

CANONICAL_TABS = [
    "top", "nfl", "x", "underreported", "world", "us", "presidential",
    "federal", "legislation", "nm", "local", "region", "technology",
    "gaming", "military", "boxoffice",
]

RANKING_SURFACES = {"top"}
SPECIAL_SURFACES = {"x", "boxoffice"}

STOPWORDS = {
    "the","a","an","and","or","but","to","of","in","on","for","with","at","by","from","as","is","are","was","were",
    "be","been","being","that","this","these","those","it","its","their","his","her","they","them","he","she","you","we",
    "will","would","could","should","may","might","after","before","over","under","into","about","amid","new","news","says","say",
    "report","reports","reported","update","latest","breaking"
}

@dataclass(frozen=True)
class TabRule:
    positives: Dict[str, float]
    negatives: Dict[str, float]
    threshold: float
    title_bonus: float = 1.25
    specificity: int = 1


def _d(items: Iterable[Tuple[str, float]]) -> Dict[str, float]:
    return dict(items)

RULES: Dict[str, TabRule] = {
    "nfl": TabRule(_d([("nfl",9),("national football league",10),("super bowl",9),("touchdown",5),("quarterback",5),("wide receiver",4),("running back",4),("linebacker",4),("training camp",5),("roster",4),("kickoff",4),("playoffs",4),("football",2)]), _d([("college football",-12),("high school football",-12),("soccer",-10),("fifa",-10),("nba",-8),("mlb",-8),("nhl",-8)]), 6.0, specificity=10),
    "gaming": TabRule(_d([("video game",9),("gaming",8),("playstation",9),("xbox",9),("nintendo",9),("steam",7),("game studio",7),("console",6),("pc gaming",9),("esports",7),("gameplay",6),("dlc",5),("rpg",4),("shooter",4),("graphics card",3),("gpu",3),("geforce",5),("radeon",5)]), _d([("casino",-12),("gambling",-12),("sportsbook",-12),("lottery",-10),("nfl",-8),("nba",-8)]), 6.0, specificity=10),
    "technology": TabRule(_d([("technology",4),("tech",3),("artificial intelligence",9),("machine learning",8),("openai",9),("chatgpt",9),("anthropic",9),("cybersecurity",9),("cyberattack",9),("data breach",9),("software",5),("semiconductor",7),("chip",4),("nvidia",7),("amd",6),("intel",6),("microsoft",5),("google",4),("apple",4),("cloud computing",7),("robotics",6),("quantum computing",8),("smartphone",5),("android",5),("iphone",5),("privacy",3)]), _d([("touchdown",-10),("nfl",-10),("recipe",-8),("box office",-8),("movie",-5),("celebrity",-5)]), 6.0, specificity=9),
    "military": TabRule(_d([("military",7),("pentagon",9),("armed forces",9),("troops",7),("air force",7),("army",6),("navy",6),("marines",7),("missile",6),("airstrike",8),("air strike",8),("drone strike",8),("warship",8),("combat",6),("battlefield",7),("war",5),("invasion",7),("ceasefire",5),("defense department",9),("centcom",9),("military operation",9)]), _d([("war on drugs",-8),("price war",-8),("trade war",-7),("culture war",-7),("console war",-8)]), 6.0, specificity=9),
    "presidential": TabRule(_d([("president trump",10),("donald trump",10),("white house",9),("president",4),("presidential",8),("executive order",8),("oval office",8),("administration",4),("press secretary",5),("cabinet",4),("commander in chief",7)]), _d([("former president",-3),("company president",-10),("university president",-10),("team president",-10)]), 7.0, specificity=9),
    "legislation": TabRule(_d([("bill",6),("legislation",9),("signed into law",10),("lawmakers",4),("statute",7),("ordinance",8),("final rule",8),("rulemaking",7),("regulation",5),("legislature",5),("house passed",7),("senate passed",7),("vote on",5),("veto",6),("enacted",7),("law takes effect",8)]), _d([("lawsuit",-5),("law firm",-8),("law enforcement",-5)]), 7.0, specificity=9),
    "federal": TabRule(_d([("congress",8),("senate",7),("house of representatives",8),("supreme court",9),("scotus",9),("department of justice",8),("doj",7),("fbi",7),("dhs",7),("federal",5),("treasury",5),("epa",5),("sec",5),("fcc",5),("irs",5),("federal court",7),("federal judge",7),("department of",4),("agency",3)]), _d([("federal reserve",-2)]), 7.0, specificity=8),
    "local": TabRule(_d([("farmington",12),("san juan county",12),("aztec",10),("bloomfield",10),("kirtland",9),("shiprock",10),("four corners",11),("durango",9),("la plata county",10),("cortez",9),("montezuma county",10),("navajo nation",9),("gallup",8),("farmington police",12),("farmington municipal",12),("san juan regional",11)]), _d([]), 7.0, specificity=12),
    "nm": TabRule(_d([("new mexico",11),("santa fe",6),("albuquerque",6),("las cruces",6),("rio rancho",6),("new mexico legislature",11),("new mexico governor",10),("nm governor",10),("nmdot",9),("new mexico state",7)]), _d([]), 7.0, specificity=10),
    "region": TabRule(_d([("arizona",6),("colorado",6),("utah",6),("southwest",7),("rocky mountain",6),("four corners region",9),("flagstaff",6),("phoenix",4),("denver",4),("salt lake city",4),("southern colorado",7),("northern arizona",7)]), _d([]), 6.0, specificity=7),
    "world": TabRule(_d([("international",5),("foreign",3),("diplomatic",5),("diplomacy",5),("united nations",7),("nato",6),("europe",3),("asia",3),("africa",3),("middle east",5),("ukraine",5),("russia",5),("china",4),("iran",5),("israel",5),("gaza",5),("france",4),("germany",4),("britain",4),("united kingdom",4),("japan",4),("india",4),("canada",4),("mexico",4)]), _d([("local weather",-7),("nfl",-8),("super bowl",-8)]), 6.0, specificity=4),
    "us": TabRule(_d([("united states",6),("u.s.",6),("american",3),("americans",3),("nationwide",5),("across the country",5),("national",2),("governor",3),("state officials",4),("state law",4),("states",2)]), _d([("nfl",-7),("super bowl",-7),("playstation",-7),("xbox",-7)]), 6.0, specificity=3),
    "underreported": TabRule(_d([("investigation",5),("public records",7),("accountability",6),("infrastructure",4),("water",3),("environmental",4),("rural",4),("tribal",5),("public health",5),("oversight",5),("audit",5),("whistleblower",7),("neglected",5),("shortage",3),("contamination",5),("toxic",4),("housing",3),("utility",3)]), _d([("celebrity",-8),("box office",-8),("game review",-8),("nfl",-6)]), 5.0, specificity=2),
    "boxoffice": TabRule(_d([("box office",10),("opening weekend",8),("weekend gross",9),("domestic gross",9),("worldwide gross",8),("theaters",4),("movie",3),("film",3),("cinema",5),("imax",6),("ticket sales",6),("release date",4)]), _d([("movie theater shooting",-8),("home theater",-8)]), 6.0, specificity=9),
    "x": TabRule(_d([("election",4),("immigration",4),("economy",4),("inflation",4),("war",4),("ai",3),("abortion",4),("healthcare",4),("supreme court",4),("congress",4),("trump",4),("climate",4),("border",4),("tariff",4)]), _d([]), 4.0, specificity=1),
    "top": TabRule(_d([("breaking",2),("major",2),("supreme court",4),("president",3),("war",3),("attack",3),("election",3),("emergency",3),("dead",3),("killed",3),("hurricane",3),("earthquake",3),("wildfire",3),("market crash",4),("ceasefire",3)]), _d([]), 0.0, specificity=0),
}

US_STATES = {"alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi","missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico","new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania","rhode island","south carolina","south dakota","tennessee","texas","utah","vermont","virginia","washington","west virginia","wisconsin","wyoming"}

def normalize(s: str) -> str:
    return " " + re.sub(r"\s+", " ", (s or "").lower()).strip() + " "

def field(item: ET.Element, name: str) -> str:
    return (item.findtext(name) or "").strip()

def text_parts(item: ET.Element) -> Tuple[str, str, str]:
    return normalize(field(item,"title")), normalize(field(item,"description")), normalize(field(item,"whyMatters"))

def phrase_present(text: str, phrase: str) -> bool:
    p=phrase.lower().strip()
    if not p: return False
    if " " in p or "." in p or "-" in p: return p in text
    return re.search(rf"\b{re.escape(p)}\b",text) is not None

def score_tab_raw(item: ET.Element, tab: str) -> float:
    rule=RULES[tab]; title,desc,why=text_parts(item); full=title+desc+why; score=0.0
    for term,weight in rule.positives.items():
        if phrase_present(full,term):
            score+=weight
            if phrase_present(title,term): score+=weight*rule.title_bonus
    for term,weight in rule.negatives.items():
        if phrase_present(full,term): score+=weight
    if tab=="us" and any(phrase_present(full,st) for st in US_STATES): score+=3.0
    return round(score,2)

def score_tab(item: ET.Element, tab: str) -> Tuple[float,List[str]]:
    rule=RULES[tab]; title,desc,why=text_parts(item); full=title+desc+why; score=0.0; evidence=[]
    for term,weight in rule.positives.items():
        if phrase_present(full,term):
            score+=weight; evidence.append("+"+term)
            if phrase_present(title,term): score+=weight*rule.title_bonus; evidence.append("+title:"+term)
    for term,weight in rule.negatives.items():
        if phrase_present(full,term): score+=weight; evidence.append("!"+term)
    if tab=="us" and any(phrase_present(full,st) for st in US_STATES): score+=3.0; evidence.append("+us-state")
    if tab=="region" and score>0 and (score_tab_raw(item,"local")>=RULES["local"].threshold or score_tab_raw(item,"nm")>=RULES["nm"].threshold): score-=5.0; evidence.append("!more-specific-geography")
    if tab=="nm" and score>0 and score_tab_raw(item,"local")>=RULES["local"].threshold: score-=5.0; evidence.append("!local-specific")
    if tab in {"world","us"}:
        for specific in ("military","technology","gaming","nfl","presidential","federal","legislation"):
            if score_tab_raw(item,specific)>=RULES[specific].threshold+2: score-=4.0; evidence.append("!specific:"+specific)
    return round(score,2),evidence

def all_scores(item: ET.Element) -> Dict[str,float]:
    return {tab:score_tab(item,tab)[0] for tab in CANONICAL_TABS}

def qualifies(item: ET.Element, tab: str) -> bool:
    if tab=="top": return True
    return score_tab(item,tab)[0]>=RULES[tab].threshold

def best_tab(item: ET.Element, include_special: bool=True) -> Tuple[str,float,Dict[str,float]]:
    scores=all_scores(item); candidates=[t for t in CANONICAL_TABS if t not in RANKING_SURFACES]
    if not include_special: candidates=[t for t in candidates if t not in SPECIAL_SURFACES]
    eligible=[t for t in candidates if scores[t]>=RULES[t].threshold]
    if not eligible:
        current=field(item,"category").lower()
        return (current if current in CANONICAL_TABS else "world",scores.get(current,0.0),scores)
    winner=max(eligible,key=lambda t:(scores[t]-RULES[t].threshold,RULES[t].specificity,scores[t]))
    return winner,scores[winner],scores

def tab_filter_decision(item: ET.Element) -> dict:
    current=field(item,"category").lower()
    if current=="top": return {"action":"keep","current":current,"target":"top","reason":"ranking-surface","scores":all_scores(item)}
    winner,score,scores=best_tab(item); current_score=scores.get(current,-999)
    if current==winner and qualifies(item,current): action,reason="keep","tab-qualified"
    elif winner and score>=RULES.get(winner,RULES["world"]).threshold: action,reason="reroute",f"stronger-tab:{winner}"
    else: action,reason="review","no-strong-tab"
    return {"action":action,"current":current,"target":winner,"score":score,"currentScore":current_score,"reason":reason,"scores":scores}

def content_tokens(item: ET.Element) -> set[str]:
    title,desc,_=text_parts(item); toks=set(re.findall(r"[a-z0-9]+",title+desc))
    return {t for t in toks if len(t)>=3 and t not in STOPWORDS}
