from pathlib import Path
import re

p = Path('scripts/update_news.py')
s = p.read_text(encoding='utf-8')

TOP_HELPERS = r'''def _top_title_terms(item):
    """Return conservative, normalized headline terms for Top-event matching."""
    title = clean(item.get('title') or '').lower()
    source = clean(item.get('source') or '').lower().strip()
    if source:
        title = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", title, flags=re.I)
    stop = {
        'the','a','an','and','or','but','for','from','with','into','over','after','before','about','amid','during',
        'this','that','these','those','says','said','new','news','latest','update','report','reported','according',
        'officials','official','will','could','would','may','can','has','have','had','was','were','are','is','be','been',
        'to','of','in','on','at','by','as','it','its','their','they','them','who','what','when','where','why','how',
        'one','two','first','second','third','today','now','more','just','also','still','ap','cnn','cbs','nbc','fox','npr',
        'bbc','reuters','times','post','associated','press'
    }
    canonical = {
        'attacks':'attack','attacked':'attack','attacking':'attack',
        'strikes':'strike','struck':'strike','striking':'strike',
        'missiles':'missile','tankers':'tanker','ships':'ship',
        'blocks':'block','blocked':'block','blocking':'block',
        'rejects':'reject','rejected':'reject','rejecting':'reject',
        'rules':'rule','ruled':'rule','ruling':'rule',
        'maps':'map','districts':'district','elections':'election',
        'votes':'vote','voting':'vote','voted':'vote',
        'restrictions':'restriction','restricts':'restriction','restricted':'restriction',
        'orders':'order','ordered':'order','lawsuits':'lawsuit',
        'recalls':'recall','recalled':'recall',
        'launches':'launch','launched':'launch',
        'arrests':'arrest','arrested':'arrest',
        'layoffs':'layoff','fires':'fire','fired':'fire',
    }
    out=set()
    for raw in re.findall(r"[a-z0-9]+", title):
        if len(raw) < 3 or raw in stop:
            continue
        out.add(canonical.get(raw, raw))
    return out


def same_top_event(a, b):
    """Conservatively match two headlines to one event.

    Top Stories should prefer a missed merge over a false Related Coverage link.
    Long RSS descriptions and broad subjects such as Trump/Iran are intentionally
    excluded from this decision.
    """
    ta, tb = _top_title_terms(a), _top_title_terms(b)
    if not ta or not tb:
        return False
    shared = ta & tb
    smaller = min(len(ta), len(tb))
    containment = len(shared) / max(1, smaller)
    jaccard = len(shared) / max(1, len(ta | tb))
    broad = {
        'trump','president','court','supreme','federal','government','state','house','senate','congress',
        'iran','iranian','israel','israeli','war','military','election','midterm','administration','white'
    }
    distinctive = shared - broad

    # Near-identical/reordered headlines.
    if len(shared) >= 5 and (containment >= 0.38 or jaccard >= 0.28):
        return True
    if len(shared) >= 4 and containment >= 0.42:
        return True

    # Three shared terms can be enough when at least one is event-specific and
    # the overlap covers a meaningful portion of the shorter headline. This
    # catches "Missouri ... court ... map" while rejecting "Trump ... court"
    # links about unrelated policy actions.
    if len(shared) >= 3 and containment >= 0.30 and distinctive:
        return True

    return False
'''

SELECTOR = r'''def select_top_stories(unique):
    """Rank distinct news events first, then retain a diverse rotating Top Stories pool."""
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)

    # Build event clusters before scoring. Multi-outlet coverage is therefore a
    # property of the event, not of one URL/headline key. The Top matcher is
    # intentionally stricter than the broader cleanup deduper because incorrect
    # Related Coverage is worse than leaving two legitimate cards separate.
    ordered = sorted(
        unique,
        key=lambda item: (impact_score(item, newest_time), item["published"]),
        reverse=True,
    )
    clusters = []
    for item in ordered:
        match = None
        for cluster in clusters:
            if any(same_top_event(member, item) for member in cluster[:4]):
                match = cluster
                break
        if match is None:
            clusters.append([item])
        else:
            match.append(item)

    ranked = []
    for cluster_id, cluster in enumerate(clusters):
        representative = max(
            cluster,
            key=lambda item: (impact_score(item, newest_time), item["published"]),
        )
        source_set = {
            source_key(item.get("source") or "Unknown")
            for item in cluster
            if source_key(item.get("source") or "Unknown")
        }
        outlet_count = max(1, len(source_set))
        coverage_boost = min(36, max(0, outlet_count - 1) * 9) + (8 if outlet_count >= 4 else 0)
        score = impact_score(representative, newest_time) + coverage_boost

        related_candidates = sorted(
            [item for item in cluster if key(item) != key(representative)],
            key=lambda item: item["published"],
            reverse=True,
        )
        seen_related_sources = {source_key(representative.get("source") or "Unknown")}
        deferred = []
        for related in related_candidates:
            src = source_key(related.get("source") or "Unknown")
            if src and src not in seen_related_sources:
                attach_related(representative, related)
                seen_related_sources.add(src)
            else:
                deferred.append(related)
            if len(representative.get('_relatedArticles', [])) >= 4:
                break
        if len(representative.get('_relatedArticles', [])) < 4:
            for related in deferred:
                attach_related(representative, related)
                if len(representative.get('_relatedArticles', [])) >= 4:
                    break

        ranked.append((score, representative["published"], outlet_count, cluster_id, representative))

    ranked.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    selected = []
    selected_clusters = set()
    seen_keys = set()
    source_counts = {}
    subject_counts = {}
    topic_counts = {}
    TOP_POOL_SIZE = 60
    VISIBLE_WINDOW = 10
    VISIBLE_SOURCE_CAP = 2
    SUBJECT_CAP = 4
    TOPIC_CAP = 8
    MAX_PER_SOURCE = 5

    def can_select(item, cluster_id, source_cap, enforce_topics=True):
        k = key(item)
        src = source_key(item.get("source") or "Unknown")
        if not k or k in seen_keys or cluster_id in selected_clusters:
            return False
        if source_counts.get(src, 0) >= source_cap:
            return False
        if enforce_topics:
            subs = subject_keys(item)
            topic = topic_key(item)
            if subs and max(subject_counts.get(x, 0) for x in subs) >= SUBJECT_CAP:
                return False
            if topic_counts.get(topic, 0) >= TOPIC_CAP:
                return False
        return True

    def add_item(item, cluster_id):
        k = key(item)
        src = source_key(item.get("source") or "Unknown")
        subs = subject_keys(item)
        topic = topic_key(item)
        selected.append(item)
        selected_clusters.add(cluster_id)
        seen_keys.add(k)
        source_counts[src] = source_counts.get(src, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        for sub in subs:
            subject_counts[sub] = subject_counts.get(sub, 0) + 1

    # The first screen should not be dominated by one publisher.
    for _, _, _, cluster_id, item in ranked:
        if len(selected) >= VISIBLE_WINDOW:
            break
        if can_select(item, cluster_id, VISIBLE_SOURCE_CAP, True):
            add_item(item, cluster_id)

    if len(selected) < VISIBLE_WINDOW:
        for _, _, _, cluster_id, item in ranked:
            if len(selected) >= VISIBLE_WINDOW:
                break
            if can_select(item, cluster_id, MAX_PER_SOURCE, True):
                add_item(item, cluster_id)

    for _, _, _, cluster_id, item in ranked:
        if len(selected) >= TOP_POOL_SIZE:
            break
        if can_select(item, cluster_id, MAX_PER_SOURCE, True):
            add_item(item, cluster_id)

    if len(selected) < TOP_POOL_SIZE:
        for _, _, _, cluster_id, item in ranked:
            if len(selected) >= TOP_POOL_SIZE:
                break
            if can_select(item, cluster_id, MAX_PER_SOURCE, False):
                add_item(item, cluster_id)

    related_count = sum(len(x.get('_relatedArticles', [])) for x in selected)
    print(
        'TOP event clusters: '
        + str(len(clusters))
        + ' events ranked; '
        + str(related_count)
        + ' related article(s) attached; '
        + str(len(selected))
        + ' rotating Top Stories retained.'
    )
    return selected
'''

# Remove an earlier Top-only matcher if this patch is being re-applied to an
# already generated collector.
s = re.sub(r'def _top_title_terms\(item\):.*?(?=def select_top_stories\(unique\):)', '', s, count=1, flags=re.S)

# Remove all prior selector copies, including malformed copies appended after main().
while True:
    start = s.find('def select_top_stories(unique):')
    if start < 0:
        break
    end = s.find('\n\ndef select_underreported(unique):', start)
    if end < 0:
        end = len(s)
    s = s[:start] + s[end:]

s = re.sub(r'\nif __name__ == ["\']__main__["\']:\n\s*main\(\)\s*', '\n', s)

nfl_line = '    "nfl": ["NFL news", "NFL injuries trades free agency", "NFL scores results"],'
if s.count(nfl_line) > 1:
    first = s.find(nfl_line)
    before = s[:first]
    after = s[first + len(nfl_line):]
    after = after.replace('\n' + nfl_line, '', 1)
    s = before + nfl_line + after
multiline_nfl = re.search(r'    "nfl": \[\n\s*"NFL news",\n\s*"NFL injuries trades free agency",\n\s*"NFL scores results",\n\s*\],', s)
if multiline_nfl:
    s = re.sub(r'\n\s*"nfl": \["NFL news", "NFL injuries trades free agency", "NFL scores results"\],', '', s)

first = s.find('SUBJECT_ALIASES = ')
second = s.find('SUBJECT_ALIASES = ', first + 1) if first >= 0 else -1
if first >= 0 and second >= 0:
    subject_end = s.find('\n\ndef subject_keys', second)
    if subject_end < 0:
        raise SystemExit('Could not locate subject_keys()')
    canonical = s[second:subject_end]
    s = s[:first] + canonical + s[subject_end:]

under = s.find('\n\ndef select_underreported(unique):')
if under < 0:
    raise SystemExit('Could not locate select_underreported()')
s = s[:under] + '\n\n' + TOP_HELPERS + '\n\n' + SELECTOR + s[under:]

if '<relatedArticles>' not in s:
    needle = '        out += [f\'<guid isPermaLink="false">{guid}</guid>\', "</item>"]'
    replacement = '''        related = item.get('_relatedArticles', [])
        if related:
            out.append('<relatedArticles>')
            for rel in related:
                out += [f'<article><title>{xml_escape(rel.get("title", ""))}</title>', f'<link>{xml_escape(rel.get("link", ""))}</link>', f'<source>{xml_escape(rel.get("source", ""))}</source></article>']
            out.append('</relatedArticles>')
        out += [f'<guid isPermaLink="false">{guid}</guid>', "</item>"]'''
    if needle not in s:
        raise SystemExit('Could not locate RSS builder')
    s = s.replace(needle, replacement, 1)

s = s.rstrip() + '\n\nif __name__ == "__main__":\n    main()\n'
p.write_text(s, encoding='utf-8')
print('Canonicalized strict event-first Top ranking with visible-page publisher diversity and related coverage.')
