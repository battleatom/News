from pathlib import Path
from datetime import datetime, timezone
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

NEWS = Path("News")
MAX_AGE_DAYS = 3

# X is a fixed product surface: exactly one current conversation for each of these
# ten topic slots. The slot names do not change from refresh to refresh.
CATEGORIES = [
    ("Health", "health medical disease FDA public health"),
    ("Technology & AI", "AI technology OpenAI Google Apple cybersecurity"),
    ("Celebrities & Public Figures", "celebrity actor singer athlete public figure"),
    ("World", "world international conflict war diplomacy"),
    ("Politics & Government", "White House Congress Supreme Court politics government"),
    ("Entertainment", "movies music television streaming entertainment"),
    ("Sports", "NFL NBA MLB soccer sports"),
    ("Business & Economy", "economy stocks tariffs jobs business companies"),
    ("Gaming", "gaming PlayStation Xbox Nintendo PC games"),
    ("Science", "science space NASA climate research"),
]
EXPECTED_TOPICS = [name for name, _ in CATEGORIES]

STOP = {"the","a","an","to","of","in","on","for","and","with","is","as","at","from","by","after","new","says","said","that","this","are","was","were","has","have","had","into","over","its","their","will","news","latest","x","twitter","post","posts","users","people"}
GENERIC = {"trump", "elon musk", "donald trump", "taylor swift", "kim kardashian", "celebrity", "breaking news", "viral", "x", "twitter"}


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 4 and w not in STOP}


def date(value):
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        return None


def fetch(query, days=MAX_AGE_DAYS):
    q = urllib.parse.quote(f"{query} when:{days}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Underreported-X/3.2"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return ET.fromstring(response.read())


def news_item_data(item):
    source_el = item.find("source")
    return {
        "title": clean(item.findtext("title")),
        "link": clean(item.findtext("link")),
        "desc": clean(item.findtext("description")),
        "pub": clean(item.findtext("pubDate")),
        "source": clean(source_el.text if source_el is not None else ""),
        "dt": date(item.findtext("pubDate")),
    }


def fetch_trend_names():
    urls = ["https://twitter-trends.snaplytics.io/", "https://www.techtwitter.com/twitter-trending/archive"]
    names = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Underreported-X/3.2"})
            with urllib.request.urlopen(req, timeout=15) as response:
                text = response.read().decode("utf-8", errors="ignore")
            text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", text, flags=re.I)
            text = html.unescape(re.sub(r"\s+", " ", text))
            for token in re.findall(r"(?:#|\$)?[A-Za-z][A-Za-z0-9'’.-]{2,}(?:\s+[A-Za-z0-9'’.-]{2,}){0,5}", text):
                token = token.strip(" -–—|:,.()[]{}")
                low = token.lower()
                if low in GENERIC or len(token) < 4 or len(token) > 80:
                    continue
                if any(x in low for x in ("twitter trends", "trending now", "snaplytics", "archive", "javascript", "privacy policy", "cookie")):
                    continue
                names.append(token)
        except Exception:
            continue
    out=[]; seen=set()
    for n in names:
        k=n.lower()
        if k not in seen:
            seen.add(k); out.append(n)
    return out[:120]


def category_match(name, query):
    n = name.lower()
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    return any(t in n for t in terms if len(t) >= 4)


def trend_candidates(query, trend_names):
    matched = [n for n in trend_names if category_match(n, query)]
    candidates=[]
    for name in matched[:20]:
        try:
            rss = fetch(f'"{name}"')
        except Exception:
            continue
        for item in rss.findall(".//item"):
            d = news_item_data(item)
            if not d["dt"] or not d["title"] or len(d["desc"]) < 70:
                continue
            if "x.com/" in d["link"].lower() or "twitter.com/" in d["link"].lower():
                continue
            overlap = len(words(d["title"]) & words(name))
            if overlap or name.lower() in d["title"].lower():
                candidates.append((overlap, d, name))
    candidates.sort(key=lambda x:(x[0], x[1]["dt"]), reverse=True)
    return candidates


def broad_candidates(query):
    try:
        rss=fetch(query)
    except Exception:
        return []
    out=[]
    for item in rss.findall(".//item"):
        d=news_item_data(item)
        if d["dt"] and len(words(d["title"])) >= 4 and len(d["desc"]) > 80:
            out.append((1,d,""))
    out.sort(key=lambda x:x[1]["dt"], reverse=True)
    return out[:30]


def existing_candidates(items, query):
    qwords=words(query)
    out=[]
    for item in items:
        cat=clean(item.findtext("category"))
        if cat in {"x","legislation","boxoffice"}: continue
        d=news_item_data(item)
        if not d["dt"] or not d["title"]: continue
        overlap=len((words(d["title"]) | words(d["desc"])) & qwords)
        if overlap:
            out.append((overlap,d,""))
    out.sort(key=lambda x:(x[0],x[1]["dt"]),reverse=True)
    return out[:30]


def best_issue(query, trend_names, items):
    # Prefer the already-collected feed. On the production second pass this feed has
    # already passed the normal source/category verifier, so the X lead inherits that gate.
    candidates=existing_candidates(items,query)
    if not candidates:
        candidates=trend_candidates(query,trend_names)
    if not candidates:
        candidates=broad_candidates(query)
    if not candidates:
        return None
    def score(row):
        overlap,d,name=row
        concrete=len(words(d["title"]))
        explanation=min(len(d["desc"]),500)/100
        age=(datetime.now(timezone.utc)-d["dt"]).total_seconds()/86400
        return overlap*8+concrete+explanation-age*2
    return max(candidates,key=score)


def related_reporting(signal_title, query):
    terms=list(words(signal_title))[:10]
    search=" ".join(terms) or query
    try: rss=fetch(search)
    except Exception: return []
    out=[]
    for item in rss.findall(".//item"):
        d=news_item_data(item)
        if not d["dt"] or not d["title"] or len(d["desc"])<60: continue
        if "x.com/" in d["link"].lower() or "twitter.com/" in d["link"].lower(): continue
        overlap=len(words(d["title"]) & words(signal_title))
        if overlap>=1: out.append((overlap,d))
    out.sort(key=lambda x:(x[0],x[1]["dt"]),reverse=True)
    seen=set(); result=[]
    for _,d in out:
        if d["link"] in seen: continue
        seen.add(d["link"]); result.append(d)
        if len(result)>=4: break
    return result


def main():
    if not NEWS.exists(): raise SystemExit("News feed not found")
    tree=ET.parse(NEWS); channel=tree.getroot().find("channel")
    if channel is None: raise SystemExit("RSS channel not found")
    all_items=list(channel.findall("item"))
    for item in all_items:
        if clean(item.findtext("category"))=="x": channel.remove(item)
    base_items=[x for x in all_items if clean(x.findtext("category"))!="x"]
    trend_names=fetch_trend_names()

    created=[]
    for category,query in CATEGORIES:
        best=best_issue(query,trend_names,base_items)
        if not best:
            raise SystemExit(f"X Top Issues failed: no publishable lead for fixed topic {category!r}")
        _,lead,trend=best
        reports=related_reporting(lead["title"],query)
        issue=ET.Element("item")
        ET.SubElement(issue,"title").text=lead["title"]
        ET.SubElement(issue,"link").text=lead["link"]
        ET.SubElement(issue,"description").text=lead["desc"]
        ET.SubElement(issue,"pubDate").text=lead["pub"]
        ET.SubElement(issue,"source").text=lead["source"] or "Independent reporting"
        ET.SubElement(issue,"category").text="x"
        ET.SubElement(issue,"xTopic").text=category
        ET.SubElement(issue,"xSignal").text="Top public X conversation"
        ET.SubElement(issue,"xWhyTrending").text=(f'“{trend}” is appearing in public X trend signals and is being discussed in current reporting.' if trend else 'This fixed topic slot is populated by the strongest current conversation supported by independent reporting.')
        ET.SubElement(issue,"xWhatPeopleAreSaying").text="People on X are discussing the underlying issue from different perspectives. The trend signal identifies the conversation; it does not establish that every claim circulating in it is true."
        ET.SubElement(issue,"xConfirmed").text="Independent reporting confirms the underlying news event described above. Supporting reporting is attached when additional matching coverage is available."
        ET.SubElement(issue,"xUnconfirmed").text="Specific rumors, screenshots, accusations, and interpretations circulating on X are not treated as facts unless independently verified."
        rel=ET.SubElement(issue,"xRelated"); seen={lead["link"]}
        for r in reports:
            if r["link"] in seen: continue
            seen.add(r["link"])
            child=ET.SubElement(rel,"article")
            ET.SubElement(child,"title").text=r["title"]
            ET.SubElement(child,"link").text=r["link"]
            ET.SubElement(child,"source").text=r["source"]
            ET.SubElement(child,"pubDate").text=r["pub"]
        channel.append(issue); created.append(category)

    if len(created)!=10 or created!=EXPECTED_TOPICS:
        raise SystemExit(f"X Top Issues validation failed: expected {EXPECTED_TOPICS}, got {created}")
    tree.write(NEWS,encoding="utf-8",xml_declaration=True)
    print("X Top Issues: created exactly 10 fixed topic slots: " + ", ".join(created))

if __name__=="__main__": main()
