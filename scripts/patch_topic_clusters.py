from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')

START = 'def select_top_stories(unique):'
END = '\n\ndef select_underreported(unique):'
if START not in s or END not in s:
    raise SystemExit('Could not locate Top Stories selector')

HELPER_MARK = 'def topic_similarity(a, b):'
if HELPER_MARK not in s:
    helper = r'''

def article_terms(item):
    """Extract meaningful headline terms for event/topic comparison."""
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    words = re.findall(r"[a-z0-9]+", text)
    stop = {
        "the","a","an","and","or","but","for","from","with","into","over","after","before","about","amid","during","this","that","these","those",
        "says","said","say","new","news","latest","update","updates","report","reports","reported","according","officials","official","will","could","would","may","can","has","have","had","was","were","are","is","be","been","being","to","of","in","on","at","by","as","it","its","their","they","them","he","she","his","her","who","what","when","where","why","how",
        "us","u","one","two","first","second","third","today","now","more","just","also","still","after","amid","via","watch","live"
    }
    normalized=[]
    for w in words:
        if len(w) < 3 or w in stop:
            continue
        if w.endswith('ies') and len(w) > 4: w=w[:-3]+'y'
        elif w.endswith('s') and not w.endswith('ss') and len(w) > 4: w=w[:-1]
        normalized.append(w)
    return set(normalized)


def topic_similarity(a, b):
    """Measure whether two headlines are really about the same event/topic."""
    ta, tb = article_terms(a), article_terms(b)
    shared = ta & tb
    if len(shared) >= 4:
        return 1.0
    if len(shared) < 2:
        return 0.0
    return len(shared) / max(1, len(ta | tb))


def same_event_topic(a, b):
    """Return True for duplicate coverage of the same developing event, not merely a shared subject."""
    sa, sb = set(subject_keys(a)), set(subject_keys(b))
    shared_subject = bool(sa & sb)
    sim = topic_similarity(a, b)
    if sim >= 0.34 and len(article_terms(a) & article_terms(b)) >= 2:
        return True
    # Named subject alone is not enough: allow separate stories about Iran,
    # Trump, etc. unless the event vocabulary also overlaps.
    if shared_subject and len(article_terms(a) & article_terms(b)) >= 2:
        return True
    return False


def add_related_article(item, related):
    item.setdefault('_relatedArticles', [])
    if not related or key(related) == key(item):
        return
    if any(key(x) == key(related) for x in item['_relatedArticles']):
        return
    item['_relatedArticles'].append(related)
    item['_relatedArticles'] = item['_relatedArticles'][:4]
'''
    insert_at = s.index('def select_top_stories(unique):')
    s = s[:insert_at] + helper + s[insert_at:]

start=s.index(START)
end=s.index(END,start)
new_func=r'''def select_top_stories(unique):
    """Select high-impact stories while clustering same-event coverage."""
    if not unique:
        return []
    newest_time=max(x["published"] for x in unique)
    coverage={}
    for item in unique:
        k=key(item)
        coverage.setdefault(k,set()).add(item["source"] or "Unknown")

    ranked=[]
    for item in unique:
        k=key(item); outlet_count=len(coverage.get(k,set()))
        score=impact_score(item,newest_time)+min(30,outlet_count*7)
        if outlet_count>=4: score+=8
        ranked.append((score,item["published"],outlet_count,item))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)

    selected=[]; seen_keys=set(); source_counts={}; subject_counts={}; topic_counts={}
    SUBJECT_CAP=3; TOPIC_CAP=5; MAX_PER_SOURCE=2

    def add(item,relaxed=False):
        k=key(item); source=source_key(item["source"] or "Unknown")
        subjects=subject_keys(item); topic=topic_key(item)
        if not k or k in seen_keys or source_counts.get(source,0)>=MAX_PER_SOURCE:
            return False
        if not relaxed:
            if subjects and max(subject_counts.get(x,0) for x in subjects)>=SUBJECT_CAP: return False
            if topic_counts.get(topic,0)>=TOPIC_CAP: return False
            # Suppress same-event coverage from the main list. Keep it attached
            # to the stronger story so readers can still follow the coverage.
            for prior in selected:
                if same_event_topic(prior,item):
                    add_related_article(prior,item)
                    return False
        selected.append(item); seen_keys.add(k)
        source_counts[source]=source_counts.get(source,0)+1
        topic_counts[topic]=topic_counts.get(topic,0)+1
        for subject in subjects: subject_counts[subject]=subject_counts.get(subject,0)+1
        return True

    for _,_,_,item in ranked:
        add(item)
        if len(selected)==30: break

    if len(selected)<30:
        for _,_,_,item in ranked:
            add(item,relaxed=True)
            if len(selected)==30: break

    clustered=sum(len(x.get('_relatedArticles',[])) for x in selected)
    print('TOP diversity subjects: '+', '.join(f'{k}={v}' for k,v in sorted(subject_counts.items(),key=lambda x:(-x[1],x[0]))[:12]))
    print('TOP diversity topics: '+', '.join(f'{k}={v}' for k,v in sorted(topic_counts.items(),key=lambda x:(-x[1],x[0]))))
    print(f'TOP event clusters: {clustered} related article(s) attached to primary stories.')
    return selected
'''
s=s[:start]+new_func+s[end:]
P.write_text(s,encoding='utf-8')
print('Installed event-level topic clustering for Top Stories.')
