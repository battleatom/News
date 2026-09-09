from pathlib import Path
import re

p = Path('scripts/update_news.py')
s = p.read_text(encoding='utf-8')

MARKER = 'SUBJECT_ALIASES = {'
if MARKER in s:
    print('Top diversity patch already present; nothing to change.')
    raise SystemExit(0)

subject_block = r'''SUBJECT_ALIASES = {
    "iran": ("iran", "iranian", "tehran"),
    "israel": ("israel", "israeli", "gaza", "idf"),
    "russia": ("russia", "russian", "moscow", "putin"),
    "ukraine": ("ukraine", "ukrainian", "kyiv", "zelensky"),
    "china": ("china", "chinese", "beijing", "xi jinping"),
    "north korea": ("north korea", "north korean", "pyongyang", "kim jong un"),
    "donald trump": ("donald trump", "trump", "president trump"),
    "congress": ("congress", "senate", "house republicans", "house democrats"),
    "supreme court": ("supreme court", "scotus"),
    "fed": ("federal reserve", "fed", "jerome powell"),
    "nato": ("nato",),
    "gulf": ("strait of hormuz", "persian gulf", "gulf states"),
    "israel-palestine": ("palestinian", "palestine", "west bank"),
    "elon musk": ("elon musk", "musk", "spacex", "tesla"),
    "meta": ("meta", "facebook", "instagram", "zuckerberg"),
    "openai": ("openai", "chatgpt"),
    "google": ("google", "alphabet"),
    "apple": ("apple", "iphone"),
    "microsoft": ("microsoft", "windows", "xbox"),
    "nvidia": ("nvidia", "geforce", "rtx"),
    "amazon": ("amazon", "aws"),
}

'''

helpers = r'''def subject_keys(item):
    """Return major named subjects represented in a headline/description."""
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    return [subject for subject, aliases in SUBJECT_ALIASES.items()
            if any(re.search(rf"\\b{re.escape(alias)}\\b", text) for alias in aliases)]


def topic_key(item):
    """Return a broad topic bucket so one subject/event type cannot crowd out others."""
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    topic_terms = [
        ("military-conflict", ("war", "airstrike", "missile", "troops", "invasion", "ceasefire", "military conflict")),
        ("disaster-weather", ("earthquake", "hurricane", "tornado", "wildfire", "flood", "drought")),
        ("crime-public-safety", ("shooting", "killed", "murder", "police", "arrested", "missing")),
        ("economy-markets", ("inflation", "recession", "stocks", "market", "tariff", "oil prices", "unemployment")),
        ("government-politics", ("congress", "senate", "supreme court", "executive order", "election", "white house")),
        ("technology", ("ai", "artificial intelligence", "cyberattack", "hack", "software", "chip", "technology")),
        ("business", ("company", "acquisition", "layoffs", "bankruptcy", "earnings", "ceo")),
        ("science-space", ("nasa", "space", "rocket", "scientists", "study", "research")),
        ("sports", ("nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball")),
    ]
    for topic, terms in topic_terms:
        if any(term in text for term in terms):
            return topic
    return "general"

'''

start = s.index('def select_top_stories(unique):')
end = s.index('\n\ndef select_underreported(unique):', start)
new_func = r'''def select_top_stories(unique):
    """Build a diverse front page instead of letting one event dominate Top Stories."""
    if not unique:
        return []
    newest_time = max(x["published"] for x in unique)
    coverage = {}
    for item in unique:
        k = key(item)
        coverage.setdefault(k, set()).add(item["source"] or "Unknown")

    ranked = []
    for item in unique:
        k = key(item)
        outlet_count = len(coverage.get(k, set()))
        score = impact_score(item, newest_time) + min(30, outlet_count * 7)
        if outlet_count >= 4:
            score += 8
        ranked.append((score, item["published"], outlet_count, item))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)

    selected, seen_keys, source_counts = [], set(), {}
    subject_counts, topic_counts = {}, {}
    SUBJECT_CAP = 3
    TOPIC_CAP = 5
    MAX_PER_SOURCE = 2

    def add(item, relaxed=False):
        k = key(item)
        source = source_key(item["source"] or "Unknown")
        subjects = subject_keys(item)
        topic = topic_key(item)
        if not k or k in seen_keys or source_counts.get(source, 0) >= MAX_PER_SOURCE:
            return False
        if not relaxed:
            if subjects and max(subject_counts.get(s, 0) for s in subjects) >= SUBJECT_CAP:
                return False
            if topic_counts.get(topic, 0) >= TOPIC_CAP:
                return False
        selected.append(item)
        seen_keys.add(k)
        source_counts[source] = source_counts.get(source, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        for subject in subjects:
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
        return True

    # Pass 1 protects subject/topic variety while keeping the strongest stories.
    for _, _, _, item in ranked:
        add(item)
        if len(selected) == 30:
            break

    # Pass 2 fills remaining slots if today's news is unusually concentrated.
    # Duplicate and publisher protections remain active.
    if len(selected) < 30:
        for _, _, _, item in ranked:
            add(item, relaxed=True)
            if len(selected) == 30:
                break

    print("TOP diversity subjects: " + ", ".join(f"{k}={v}" for k, v in sorted(subject_counts.items(), key=lambda x: (-x[1], x[0]))[:12]))
    print("TOP diversity topics: " + ", ".join(f"{k}={v}" for k, v in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))))
    return selected
'''

# Insert helpers immediately before the selector, then replace only that selector.
s = s[:start] + subject_block + helpers + new_func + s[end:]
p.write_text(s, encoding='utf-8')
print('Added subject/topic diversity controls to Top Stories.')
