from pathlib import Path
import re

p = Path('scripts/update_news.py')
s = p.read_text(encoding='utf-8')

start = s.find('def same_event_topic(a, b):')
end = s.find('\n\ndef attach_related', start)
if start < 0 or end < 0:
    raise SystemExit('Could not locate same_event_topic block')

replacement = r'''def same_event_topic(a, b):
    """Detect redundant coverage of the same real-world event without collapsing a whole subject."""
    ta, tb = article_terms(a), article_terms(b)
    shared = ta & tb
    sa, sb = set(subject_keys(a)), set(subject_keys(b))
    shared_subjects = sa & sb
    topic_a, topic_b = topic_key(a), topic_key(b)

    # Title terms are more useful for event matching than long publisher descriptions.
    title_a = set(re.findall(r"[a-z0-9]+", (a.get('title') or '').lower()))
    title_b = set(re.findall(r"[a-z0-9]+", (b.get('title') or '').lower()))
    title_stop = {"the","a","an","and","or","but","for","from","with","into","over","after","before","about","amid","during","this","that","these","those","says","said","new","news","latest","update","report","reported","according","officials","official","will","could","would","may","can","has","have","had","was","were","are","is","be","been","to","of","in","on","at","by","as","it","its","their","they","them","who","what","when","where","why","how","us","one","two","first","second","third","today","now","more","just","also","still"}
    title_a = {w for w in title_a if len(w) >= 3 and w not in title_stop}
    title_b = {w for w in title_b if len(w) >= 3 and w not in title_stop}
    title_shared = title_a & title_b

    # Strong phrase/event anchors. These distinguish an actual event from a broad subject.
    event_groups = {
        'military': {'war','warfare','siege','airstrike','airstrikes','missile','missiles','strike','strikes','bombing','bombed','troops','invasion','invades','invaded','ceasefire','fighting','battle','battles','offensive','attack','attacks','attacked','retaliation','retaliates','retaliatory','shelling','raid','raids'},
        'recall': {'recall','recalls','recalled','contamination','contaminated','salmonella','listeria','outbreak','outbreaks','safety'},
        'disaster': {'earthquake','hurricane','tornado','wildfire','flood','flooding','landslide','eruption','evacuation','evacuations'},
        'crime': {'shooting','shootings','murder','murdered','homicide','arrest','arrested','missing','kidnapped','robbery','stabbing','stabbings','charged','indicted'},
        'government': {'bill','bills','vote','votes','voted','law','lawsuit','ruling','rules','ruled','order','orders','executive','legislation','hearing','hearings','impeach','impeachment'},
        'business': {'acquisition','acquires','acquired','merger','merges','layoffs','laid','bankruptcy','bankrupt','closure','closes','closed','earnings','recall'},
        'technology': {'breach','hack','hacked','hackers','outage','outages','vulnerability','vulnerabilities','launch','launches','launched','shutdown','shuts','updates','update'},
        'sports': {'game','games','match','matches','injury','injured','trade','trades','signed','signs','score','scores','playoffs','championship'},
    }

    def event_groups_for(terms):
        return {name for name, words in event_groups.items() if terms & words}

    groups_a = event_groups_for(ta | title_a)
    groups_b = event_groups_for(tb | title_b)
    shared_groups = groups_a & groups_b

    # Exact/near-exact lexical overlap remains the safest signal.
    if len(shared) >= 4:
        return True
    if len(shared) >= 3 and len(shared) / max(1, len(ta | tb)) >= 0.24:
        return True
    if len(title_shared) >= 3:
        return True

    # Same named subject + same event class + at least one meaningful event anchor.
    # This catches examples like "war in Iran" / "Iran under siege" while allowing
    # unrelated Iran stories such as sanctions, diplomacy, or elections to coexist.
    if shared_subjects and shared_groups:
        if len(title_shared) >= 1 and len(shared) >= 1:
            return True
        if len(shared) >= 2:
            return True

    # If titles share a named subject and two event-specific words, treat as one event
    # even when descriptions use different wording.
    if shared_subjects and len(title_shared) >= 2 and shared_groups:
        return True

    # Recall/safety stories commonly use different wording ("recalls eggs" vs
    # "national egg recall"). Two shared terms plus the same event class is enough.
    if topic_a == topic_b and topic_a in {'recall-food-safety','disaster-weather','crime-public-safety'}:
        if len(shared) >= 2 and (shared_groups or len(title_shared) >= 1):
            return True

    return False
'''

s = s[:start] + replacement + s[end:]
p.write_text(s, encoding='utf-8')
print('Applied stronger event-level duplicate detection.')
