from pathlib import Path
import re

p = Path('scripts/update_news.py')
s = p.read_text(encoding='utf-8')

# Normalize the NFL collector entry so scheduled runs remain idempotent.
nfl_line = '    "nfl": ["NFL news", "NFL injuries trades free agency", "NFL scores results"],'
s = re.sub(r'(?:\n?' + re.escape(nfl_line) + r'){1,}', '\n' + nfl_line, s)

SUBJECT_ALIASES = {
    "iran": ("iran", "iranian", "tehran"), "israel": ("israel", "israeli", "gaza", "idf"),
    "russia": ("russia", "russian", "moscow", "putin"), "ukraine": ("ukraine", "ukrainian", "kyiv", "zelensky"),
    "china": ("china", "chinese", "beijing", "xi jinping"), "north korea": ("north korea", "north korean", "pyongyang", "kim jong un"),
    "donald trump": ("donald trump", "trump", "president trump"), "congress": ("congress", "senate", "house republicans", "house democrats"),
    "supreme court": ("supreme court", "scotus"), "fed": ("federal reserve", "fed", "jerome powell"),
    "nato": ("nato",), "gulf": ("strait of hormuz", "persian gulf", "gulf states"),
    "israel-palestine": ("palestinian", "palestine", "west bank"), "elon musk": ("elon musk", "musk", "spacex", "tesla"),
    "meta": ("meta", "facebook", "instagram", "zuckerberg"), "openai": ("openai", "chatgpt"),
    "google": ("google", "alphabet"), "apple": ("apple", "iphone"), "microsoft": ("microsoft", "windows", "xbox"),
    "nvidia": ("nvidia", "geforce", "rtx"), "amazon": ("amazon", "aws"), "walmart": ("walmart", "wal-mart"),
}

HELPERS = r'''
def subject_keys(item):
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    return [subject for subject, aliases in SUBJECT_ALIASES.items()
            if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases)]


def topic_key(item):
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    groups = [
        ("military-conflict", ("war", "airstrike", "missile", "troops", "invasion", "ceasefire", "military conflict")),
        ("recall-food-safety", ("recall", "recalled", "food safety", "contamination", "salmonella", "listeria", "eggs", "egg")),
        ("disaster-weather", ("earthquake", "hurricane", "tornado", "wildfire", "flood", "drought")),
        ("crime-public-safety", ("shooting", "killed", "murder", "police", "arrested", "missing")),
        ("economy-markets", ("inflation", "recession", "stocks", "market", "tariff", "oil prices", "unemployment")),
        ("government-politics", ("congress", "senate", "supreme court", "executive order", "election", "white house")),
        ("technology", ("ai", "artificial intelligence", "cyberattack", "hack", "software", "chip", "technology")),
        ("business", ("company", "acquisition", "layoffs", "bankruptcy", "earnings", "ceo")),
        ("science-space", ("nasa", "space", "rocket", "scientists", "study", "research")),
        ("sports", ("nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball")),
    ]
    for topic, terms in groups:
        if any(term in text for term in terms): return topic
    return "general"


def article_terms(item):
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    words = re.findall(r"[a-z0-9]+", text)
    stop = {"the","a","an","and","or","but","for","from","with","into","over","after","before","about","amid","during","this","that","these","those","says","said","say","new","news","latest","update","updates","report","reports","reported","according","officials","official","will","could","would","may","can","has","have","had","was","were","are","is","be","been","being","to","of","in","on","at","by","as","it","its","their","they","them","who","what","when","where","why","how","us","one","two","first","second","third","today","now","more","just","also","still","amid"}
    out=set()
    for w in words:
        if len(w)<3 or w in stop: continue
        if w.endswith('ies') and len(w)>4: w=w[:-3]+'y'
        elif w.endswith('s') and not w.endswith('ss') and len(w)>4: w=w[:-1]
        out.add(w)
    return out


def same_event_topic(a, b):
    ta,tb=article_terms(a),article_terms(b)
    shared=ta & tb
    sa,sb=set(subject_keys(a)),set(subject_keys(b))
    # Strong shared event vocabulary: e.g. "Walmart recalls eggs" / "national egg recall".
    if len(shared)>=4: return True
    if len(shared)>=2 and len(shared)/max(1,len(ta|tb))>=0.30: return True
    # A named subject alone is not enough; two Iran stories can both remain if
    # they concern different events. Shared event words make them a cluster.
    if sa & sb and len(shared)>=2: return True
    return False


def attach_related(primary, related):
    if key(primary)==key(related): return
    related_list=primary.setdefault('_relatedArticles', [])
    if any(key(x)==key(related) for x in related_list): return
    related_list.append(related)
    primary['_relatedArticles']=related_list[:4]
'''

# Always replace the helper block and selector so this patch remains canonical on every workflow run.
helper_start = s.find('def subject_keys(item):')
selector_start = s.find('def select_top_stories(unique):')
under_start = s.find('\n\ndef select_underreported(unique):', selector_start)
if selector_start < 0 or under_start < 0:
    raise SystemExit('Could not locate Top Stories selector')
if helper_start >= 0 and helper_start < selector_start:
    s = s[:helper_start] + s[selector_start:]
    selector_start = helper_start
    under_start = s.find('\n\ndef select_underreported(unique):', selector_start)
subject_literal = 'SUBJECT_ALIASES = ' + repr(SUBJECT_ALIASES) + '\n'
s = s[:selector_start] + subject_literal + HELPERS + s[under_start:]
selector_start = s.find('def select_top_stories(unique):')
under_start = s.find('\n\ndef select_underreported(unique):', selector_start)

SELECTOR = r'''def select_top_stories(unique):
    """Keep distinct subjects/events in Top Stories and attach suppressed coverage."""
    if not unique: return []
    newest_time=max(x["published"] for x in unique)
    coverage={}
    for item in unique:
        coverage.setdefault(key(item),set()).add(item["source"] or "Unknown")
    ranked=[]
    for item in unique:
        outlet_count=len(coverage.get(key(item),set()))
        score=impact_score(item,newest_time)+min(30,outlet_count*7)+(8 if outlet_count>=4 else 0)
        ranked.append((score,item["published"],outlet_count,item))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
    selected=[];seen_keys=set();source_counts={};subject_counts={};topic_counts={}
    SUBJECT_CAP=3;TOPIC_CAP=5;MAX_PER_SOURCE=2
    for _,_,_,item in ranked:
        k=key(item);src=source_key(item.get("source") or "Unknown");subs=subject_keys(item);topic=topic_key(item)
        if not k or k in seen_keys or source_counts.get(src,0)>=MAX_PER_SOURCE: continue
        if subs and max(subject_counts.get(x,0) for x in subs)>=SUBJECT_CAP: continue
        if topic_counts.get(topic,0)>=TOPIC_CAP: continue
        clustered=False
        for prior in selected:
            if same_event_topic(prior,item):
                attach_related(prior,item);clustered=True;break
        if clustered: continue
        selected.append(item);seen_keys.add(k);source_counts[src]=source_counts.get(src,0)+1;topic_counts[topic]=topic_counts.get(topic,0)+1
        for sub in subs: subject_counts[sub]=subject_counts.get(sub,0)+1
        if len(selected)>=30: break
    # Fill only with genuinely different stories; do not reintroduce a clustered event.
    if len(selected)<30:
        for _,_,_,item in ranked:
            k=key(item);src=source_key(item.get("source") or "Unknown")
            if not k or k in seen_keys or source_counts.get(src,0)>=MAX_PER_SOURCE: continue
            if any(same_event_topic(prior,item) for prior in selected):
                for prior in selected:
                    if same_event_topic(prior,item): attach_related(prior,item);break
                continue
            selected.append(item);seen_keys.add(k);source_counts[src]=source_counts.get(src,0)+1
            if len(selected)>=30: break
    clustered=sum(len(x.get('_relatedArticles',[])) for x in selected)
    print('TOP event clusters: '+str(clustered)+' related article(s) attached to primary stories.')
    return selected
'''
s=s[:selector_start]+SELECTOR+s[under_start:]

# Extend RSS output with related coverage links.
if '<relatedArticles>' not in s:
    old="""        out += [\"<item>\", f'<title>{xml_escape(item[\"title\"])}</title>', f'<link>{xml_escape(item[\"link\"])}</link>', f'<description>{xml_escape(item.get(\"description\", \"\"))}</description>', f'<pubDate>{xml_escape(item[\"pubDate\"])}</pubDate>', f'<source>{xml_escape(item[\"source\"])}</source>', f'<category>{item[\"category\"]}</category>', f'<region>{xml_escape(item.get(\"region\", \"\"))}</region>', f'<whyMatters>{xml_escape(item.get(\"whyMatters\", \"\"))}</whyMatters>', f'<guid isPermaLink=\"false\">{guid}</guid>', \"</item>\"]"""
    new="""        out += [\"<item>\", f'<title>{xml_escape(item[\"title\"])}</title>', f'<link>{xml_escape(item[\"link\"])}</link>', f'<description>{xml_escape(item.get(\"description\", \"\"))}</description>', f'<pubDate>{xml_escape(item[\"pubDate\"])}</pubDate>', f'<source>{xml_escape(item[\"source\"])}</source>', f'<category>{item[\"category\"]}</category>', f'<region>{xml_escape(item.get(\"region\", \"\"))}</region>', f'<whyMatters>{xml_escape(item.get(\"whyMatters\", \"\"))}</whyMatters>']
        related=item.get('_relatedArticles', [])
        if related:
            out.append('<relatedArticles>')
            for rel in related:
                out += [f'<article><title>{xml_escape(rel.get(\"title\",\"\"))}</title>', f'<link>{xml_escape(rel.get(\"link\",\"\"))}</link>', f'<source>{xml_escape(rel.get(\"source\",\"\"))}</source></article>']
            out.append('</relatedArticles>')
        out += [f'<guid isPermaLink=\"false\">{guid}</guid>', \"</item>\"]"""
    if old not in s:
        raise SystemExit('Could not locate RSS builder')
    s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('Applied event-level Top Stories clustering and related-coverage RSS output.')
