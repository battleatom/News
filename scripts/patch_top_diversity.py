from pathlib import Path
import re

p = Path('scripts/update_news.py')
s = p.read_text(encoding='utf-8')

SELECTOR = r'''def select_top_stories(unique):
    """Rank distinct news events first, then retain a diverse rotating Top Stories pool."""
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)

    # Build event clusters before scoring. Multi-outlet coverage is therefore a
    # property of the event, not of one URL/headline key.
    ordered = sorted(
        unique,
        key=lambda item: (impact_score(item, newest_time), item["published"]),
        reverse=True,
    )
    clusters = []
    for item in ordered:
        match = None
        for cluster in clusters:
            # Compare against a few members so differently worded follow-ups can
            # join the same event without letting one broad topic swallow others.
            if any(same_event_topic(member, item) for member in cluster[:4]):
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

        # Related coverage prefers distinct publishers first, then the newest
        # remaining reports. This makes the coverage drawer more useful.
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

    # If an unusually small source pool prevents ten stories, fill the visible
    # window while preserving the normal whole-pool source cap.
    if len(selected) < VISIBLE_WINDOW:
        for _, _, _, cluster_id, item in ranked:
            if len(selected) >= VISIBLE_WINDOW:
                break
            if can_select(item, cluster_id, MAX_PER_SOURCE, True):
                add_item(item, cluster_id)

    # Fill the deeper rotation while preserving subject/topic and source variety.
    for _, _, _, cluster_id, item in ranked:
        if len(selected) >= TOP_POOL_SIZE:
            break
        if can_select(item, cluster_id, MAX_PER_SOURCE, True):
            add_item(item, cluster_id)

    # Final fallback only relaxes topic caps; event and publisher caps remain.
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

# Remove all prior selector copies, including the malformed copy appended after main().
while True:
    start = s.find('def select_top_stories(unique):')
    if start < 0:
        break
    end = s.find('\n\ndef select_underreported(unique):', start)
    if end < 0:
        end = len(s)
    s = s[:start] + s[end:]

# Remove any executable entry point; it is restored at the end below.
s = re.sub(r'\nif __name__ == ["\']__main__["\']:\n\s*main\(\)\s*', '\n', s)

# Canonicalize duplicate NFL dictionary entries. Keep the first list-valued definition.
nfl_line = '    "nfl": ["NFL news", "NFL injuries trades free agency", "NFL scores results"],'
if s.count(nfl_line) > 1:
    first = s.find(nfl_line)
    before = s[:first]
    after = s[first + len(nfl_line):]
    after = after.replace('\n' + nfl_line, '', 1)
    s = before + nfl_line + after
# If both a multiline NFL entry and the legacy one-line entry exist, remove the legacy duplicate.
multiline_nfl = re.search(r'    "nfl": \[\n\s*"NFL news",\n\s*"NFL injuries trades free agency",\n\s*"NFL scores results",\n\s*\],', s)
if multiline_nfl:
    s = re.sub(r'\n\s*"nfl": \["NFL news", "NFL injuries trades free agency", "NFL scores results"\],', '', s)

# Remove duplicate SUBJECT_ALIASES assignments and retain the final/canonical one.
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
s = s[:under] + '\n\n' + SELECTOR + s[under:]

# Restore a single related-coverage RSS writer if needed.
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
print('Canonicalized event-first Top ranking with visible-page publisher diversity and related coverage.')
