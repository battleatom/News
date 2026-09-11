from pathlib import Path
import re
import xml.etree.ElementTree as ET

NEWS = Path('News')

TECH_ANCHORS = (
    'ai ', 'artificial intelligence', 'machine learning', 'cybersecurity', 'data breach',
    'software', 'hardware', 'computer', 'laptop', 'smartphone', 'iphone', 'android',
    'apple', 'google', 'microsoft', 'nvidia', 'amd', 'intel', 'meta ai', 'openai',
    'anthropic', 'chip', 'semiconductor', 'gpu', 'cpu', 'robot', 'robotics',
    'quantum', 'cloud computing', 'browser', 'internet', 'privacy', 'encryption',
    'social media', 'app ', 'apps ', 'satellite', 'spacex', 'tesla',
    'virtual reality', 'augmented reality', 'vr ', 'device', 'operating system',
)

FEDERAL_ANCHORS = (
    'fcc', 'ftc', 'fda', 'epa', 'sec ', 'doj', 'justice department', 'congress',
    'senate', 'house ', 'white house', 'federal court', 'supreme court',
    'federal government', 'federal agency', 'antitrust', 'regulator', 'regulation',
)

WORLD_ANCHORS = (
    'climate change', 'global warming', 'hottest month', 'temperature record',
    'united nations', 'international', 'global ', 'worldwide',
)

ENTERTAINMENT_ANCHORS = (
    'broadway', 'hbo max', 'netflix', 'disney+', 'streaming series', 'tv show',
    'television series', 'box office', 'actor ', 'actress ', 'movie ', 'film ',
)

JUNK_PATTERNS = (
    r'^watch\s+.+stream', r'^question\s*[-:]', r'^help\s*[-:]', r'^support\s*[-:]',
    r'^how do i\b', r'^ask\s+.+:', r'\bstream live sports\b', r'\bwatch live\b',
    r'\blive sports &\b', r'\bhomepage\b', r'\bdaily email digest\b',
)


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def text(item, tag):
    return clean(item.findtext(tag))


def raw(item):
    desc = text(item, 'description')
    # Content-brief fallbacks can begin with a category label. Do not let that
    # generated label prove its own classification on later refreshes/tests.
    desc = re.sub(r'^(?:Technology|International|Federal|U\.S\.|Local) reporting indicates\s+', '', desc, flags=re.I)
    return f"{text(item, 'title')} {desc}".lower()


def has_any(value, terms):
    return any(term in value for term in terms)


def is_junk(item):
    title = text(item, 'title').lower()
    body = raw(item)
    return any(re.search(pattern, title, flags=re.I) for pattern in JUNK_PATTERNS) or 'posts from this author is expected to be added to your daily email digest' in body


def classify_technology(item):
    body = raw(item)
    # Explicit FCC/government stories are Federal unless the regulated subject
    # is itself clearly a technology issue such as AI, privacy or chips.
    federal = has_any(body, FEDERAL_ANCHORS)
    tech = has_any(body, TECH_ANCHORS)
    strong_regulated_tech = any(term in body for term in ('artificial intelligence',' ai ','privacy','cybersecurity','semiconductor','chip','telecom','broadband','social media','software','app '))
    if federal and not strong_regulated_tech:
        return 'federal'
    # Climate/temperature records belong in World unless the actual subject is
    # a technology response or measurement system.
    if has_any(body, WORLD_ANCHORS) and not any(term in body for term in ('climate technology','carbon capture','battery','sensor','satellite technology')):
        return 'world'
    # Entertainment from a technology publisher is not Technology merely
    # because it mentions a streaming service.
    if has_any(body, ENTERTAINMENT_ANCHORS) and not any(term in body for term in ('streaming technology','codec','device','app ','platform technology')):
        return None
    return 'technology' if tech else None


def main():
    if not NEWS.exists():
        raise SystemExit('News feed not found')
    tree = ET.parse(NEWS)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')

    removed = 0
    rerouted = 0
    tech_rejected = 0
    for item in list(channel.findall('item')):
        category = text(item, 'category')
        if is_junk(item):
            channel.remove(item)
            removed += 1
            continue
        if category == 'technology':
            target = classify_technology(item)
            if target is None:
                channel.remove(item)
                tech_rejected += 1
                continue
            if target != category:
                category_el = item.find('category')
                if category_el is not None:
                    category_el.text = target
                rerouted += 1

    tree.write(NEWS, encoding='utf-8', xml_declaration=True)
    print(f'Category relevance gate: {removed} junk removed, {tech_rejected} off-topic Technology removed, {rerouted} Technology stories rerouted.')


if __name__ == '__main__':
    main()
