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
        "include": {"president","white house","administration","executive order","presidential"},
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

LEGISLATION_PATTERNS = (
    r"\b(?:bill|legislation|statute|law|regulation|rulemaking|proposed rule|final rule|rule change|regulatory action)\b",
    r"\bexecutive order\s+\d+\b",
    r"\b(?:house|senate) (?:bill|resolution|joint resolution)\b",
    r"\b(?:h\.?\s*r\.?|s\.?|h\.?\s*res\.?|s\.?\s*res\.?|h\.?\s*j\.?\s*res\.?|s\.?\s*j\.?\s*res\.?)\s*\d+\b",
    r"\bpublic inspection\b.*\b(?:rule|regulation|regulatory|exchange|commission)\b",
)

def _text(story) -> str:
    return re.sub(r"\s+", " ", f"{story.title} {story.summary} {story.source}".lower()).strip()

def _content_text(story) -> str:
    return re.sub(r"\s+", " ", f"{story.title} {story.summary}".lower()).strip()

def _legislation_relevant(story) -> bool:
    text=_content_text(story)
    if not text or len(re.sub(r"[^a-z0-9]+","",text))<12:
        return False
    if re.fullmatch(r"[-\s]*(?:congress\.gov)?[-\s]*", text):
        return False
    return any(re.search(pattern,text,re.I) for pattern in LEGISLATION_PATTERNS)

def relevant_to_category(story) -> bool:
    rules = CATEGORY_RULES.get(story.category)
    if not rules:
        return True
    text = _text(story)
    if any(term in text for term in rules["exclude"]):
        return False
    if story.category=="legislation":
        return _legislation_relevant(story)
    includes = rules["include"]
    return not includes or any(term in text for term in includes)
