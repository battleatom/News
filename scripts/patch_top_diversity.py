from pathlib import Path
import re

p = Path('scripts/update_news.py')
s = p.read_text(encoding='utf-8')

SELECTOR = r'''def select_top_stories(unique):
    """Keep a deep, diverse pool of distinct Top Stories and attach suppressed coverage."""
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)
    coverage = {}
    for item in unique:
        coverage.setdefault(key(item), set()).add(item.get("source") or "Unknown")
    ranked = []
    for item in unique:
        outlet_count = len(coverage.get(key(item), set()))
        score = impact_score(item, newest_time) + min(30, outlet_count * 7) + (8 if outlet_count >= 4 else 0)
        ranked.append((score, item["published"], outlet_count, item))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected = []
    seen_keys = set()
    source_counts = {}
    subject_counts = {}
    topic_counts = {}
    TOP_POOL_SIZE = 60
    SUBJECT_CAP = 4
    TOPIC_CAP = 8
    MAX_PER_SOURCE = 5
    for _, _, _, item in ranked:
        k = key(item); src = source_key(item.get("source") or "Unknown")
        subs = subject_keys(item); topic = topic_key(item)
        if not k or k in seen_keys or source_counts.get(src, 0) >= MAX_PER_SOURCE: continue
        if subs and max(subject_counts.get(x, 0) for x in subs) >= SUBJECT_CAP: continue
        if topic_counts.get(topic, 0) >= TOPIC_CAP: continue
        related = next((prior for prior in selected if same_event_topic(prior, item)), None)
        if related is not None:
            attach_related(related, item); continue
        selected.append(item); seen_keys.add(k)
        source_counts[src] = source_counts.get(src, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        for sub in subs: subject_counts[sub] = subject_counts.get(sub, 0) + 1
        if len(selected) >= TOP_POOL_SIZE: break
    if len(selected) < TOP_POOL_SIZE:
        for _, _, _, item in ranked:
            k = key(item); src = source_key(item.get("source") or "Unknown")
            if not k or k in seen_keys or source_counts.get(src, 0) >= MAX_PER_SOURCE: continue
            related = next((prior for prior in selected if same_event_topic(prior, item)), None)
            if related is not None:
                attach_related(related, item); continue
            selected.append(item); seen_keys.add(k)
            source_counts[src] = source_counts.get(src, 0) + 1
            if len(selected) >= TOP_POOL_SIZE: break
    print('TOP event clusters: ' + str(sum(len(x.get('_relatedArticles', [])) for x in selected)) + ' related article(s) attached to primary stories; ' + str(len(selected)) + ' rotating Top Stories retained.')
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
print('Canonicalized a 60-story rotating Top pool, preserved topic/source diversity, repaired update_news ordering, and kept related coverage.')
