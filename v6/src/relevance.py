from __future__ import annotations
import re

CATEGORY_RULES = {
    "technology": {
        "include": {"ai","artificial intelligence","cyber","security","software","hardware","chip","semiconductor","apple","google","microsoft","openai","meta","amazon","cloud","robot","computer","phone","android","iphone","internet"},
        "exclude": {"football","nfl","nba","mlb","movie review","box office","celebrity"},
    },
    "gaming": {
        "include": {"game","gaming","playstation","xbox","nintendo","steam","pc gaming","console","gpu","geforce","radeon","esports"},
        "exclude": {"football game","election","congress","senate","white house"},
    },
    "military": {
        "include": {"military","pentagon","army","navy","air force","marine","troops","missile","war","defense","defence","airstrike","drone","nato"},
        "exclude": {"sports","video game","movie","album"},
    },
    "entertainment": {
        "include": {"film","movie","television","tv","music","actor","actress","director","studio","netflix","disney","hbo","album","tour","streaming"},
        "exclude": {"congress","senate","military strike","cyberattack"},
    },
    "nfl": {
        "include": {"nfl","football","quarterback","touchdown","super bowl","roster","injury","trade","draft"},
        "exclude": {"college football","soccer","nba","mlb"},
    },
    "presidential": {
        "include": set(),
        "exclude": {"sports president","company president"},
    },
    "federal": {
        "include": {"congress","senate","house","supreme court","doj","fbi","federal","agency","department"},
        "exclude": {"federal league","sports"},
    },
    "legislation": {
        "include": set(),
        "exclude": {"sports rule","game rule"},
    },
    "nm": {
        "include": {"new mexico","albuquerque","santa fe","las cruces","farmington","san juan county","gallup","roswell"},
        "exclude": set(),
    },
    "local": {
        "include": {"farmington","san juan county","aztec","bloomfield","shiprock","four corners"},
        "exclude": set(),
    },
    "region": {
        "include": {"new mexico","arizona","colorado","utah","four corners","southwest"},
        "exclude": set(),
    },
}

US_PRESIDENTIAL_DIRECT_PATTERNS = (
    r"\bdonald trump\b",r"\bpresident trump\b",r"\btrump administration\b",r"\bthe white house\b|\bwhite house\b",
    r"\bpresident of the united states\b",r"\bu\.?s\.? president\b",r"\boval office\b",r"\bvice president vance\b",
    r"\bjd vance\b|\bj\.d\. vance\b",r"\bwhite house press secretary\b",
)
US_PRESIDENTIAL_ACTION_PATTERNS=(r"\bexecutive order\b",r"\bpresidential (?:action|memorandum|proclamation)\b",r"\bcabinet meeting\b")
US_CONTEXT_PATTERNS=(r"\bunited states\b",r"\bu\.?s\.?\b",r"\bamerican\b",r"\bwhite house\b")
FORMER_OFFICE_PATTERNS=(r"\bformer president\b",r"\bformer vice president\b",r"\bex-president\b",r"\bex-vice president\b")
LEGISLATION_PATTERNS = (
    r"\b(?:proposed|final|interim|emergency) rule\b",r"\brulemaking\b",r"\bregulation(?:s| change| changes| proposal| proposals)?\b",
    r"\bregulatory (?:action|proposal|change|changes|notice)\b",r"\b(?:bill|measure|legislation) (?:introduced|filed|passed|approved|signed|vetoed|enacted|advances?|clears?|would|to)\b",
    r"\b(?:introduced|filed|passed|approved|signed|vetoed|enacted) (?:a |the )?(?:bill|measure|legislation)\b",r"\bsigned (?:a |the )?[^.]{0,80}\binto law\b",
    r"\benacted (?:into law|legislation|statute)\b",r"\bstatute(?:s| amendment| amendments)?\b",r"\bexecutive order\s+\d+\b",
    r"\b(?:house|senate) (?:bill|resolution|joint resolution)\b",r"\b(?:h\.?\s*r\.?|s\.?|h\.?\s*res\.?|s\.?\s*res\.?|h\.?\s*j\.?\s*res\.?|s\.?\s*j\.?\s*res\.?)\s*\d+\b",
    r"\bpublic inspection\b.*\b(?:proposed rule|final rule|rulemaking|regulation|regulatory|exchange|commission)\b",r"\b(?:appropriations?|authorization) act\b",
)

def _text(story)->str:return re.sub(r"\s+"," ",f"{story.title} {story.summary} {story.source}".lower()).strip()
def _content_text(story)->str:return re.sub(r"\s+"," ",f"{story.title} {story.summary}".lower()).strip()

def _presidential_relevant(story)->bool:
    text=_content_text(story)
    if not text:return False
    direct=any(re.search(pattern,text,re.I) for pattern in US_PRESIDENTIAL_DIRECT_PATTERNS)
    if any(re.search(pattern,text,re.I) for pattern in FORMER_OFFICE_PATTERNS) and not direct:return False
    if direct:return True
    return any(re.search(pattern,text,re.I) for pattern in US_CONTEXT_PATTERNS) and any(re.search(pattern,text,re.I) for pattern in US_PRESIDENTIAL_ACTION_PATTERNS)

def _legislation_relevant(story)->bool:
    text=_content_text(story)
    if not text or len(re.sub(r"[^a-z0-9]+","",text))<12:return False
    if re.fullmatch(r"[-\s]*(?:congress\.gov)?[-\s]*",text):return False
    return any(re.search(pattern,text,re.I) for pattern in LEGISLATION_PATTERNS)

def _underreported_relevant(story)->bool:
    title=re.sub(r"[^a-z0-9]+"," ",(story.title or "").lower()).strip()
    summary=re.sub(r"\s+"," ",(story.summary or "").strip())
    source=(story.source or "").strip().lower()
    words=[w for w in title.split() if len(w)>=3]
    if len(words)<=1:return False
    residual=summary.lower()
    for token in sorted((title,source),key=len,reverse=True):
        if token:residual=residual.replace(token," ")
    residual=re.sub(r"https?://\S+|\b[a-z0-9.-]+\.(?:com|org|net|gov|edu)\b"," ",residual)
    residual=re.sub(r"[^a-z0-9]+"," ",residual).strip()
    residual_words=[w for w in residual.split() if len(w)>=3]
    if len(words)<=2 and (len(residual)<55 or len(residual_words)<8):return False
    if len(words)<=3 and len(residual_words)<5:return False
    return True

def relevant_to_category(story)->bool:
    if story.category=="underreported":return _underreported_relevant(story)
    rules=CATEGORY_RULES.get(story.category)
    if not rules:return True
    text=_text(story)
    if any(term in text for term in rules["exclude"]):return False
    if story.category=="presidential":return _presidential_relevant(story)
    if story.category=="legislation":return _legislation_relevant(story)
    includes=rules["include"]
    return not includes or any(term in text for term in includes)
