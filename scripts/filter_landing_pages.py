import re
import xml.etree.ElementTree as ET
from pathlib import Path

NEWS_FILE = Path('News')

# Strong landing-page signatures only. These are publisher/navigation pages, not
# individual news stories, and can otherwise survive similarity dedupe because
# their titles contain a location plus generic publisher branding.
LANDING_PATTERNS = (
    re.compile(r'\bbreaking news\s*,\s*latest news(?:\s+and\s+videos)?\b', re.I),
    re.compile(r'\blatest news\s*,\s*weather(?:\s*(?:and|&)\s*sports)?\b', re.I),
    re.compile(r'\bnews headlines(?:\s*,\s*weather)?\b', re.I),
)


def clean(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip()


def is_landing_page(item) -> bool:
    title = clean(item.findtext('title'))
    if not title:
        return True
    return any(pattern.search(title) for pattern in LANDING_PATTERNS)


def main():
    tree = ET.parse(NEWS_FILE)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')

    items = channel.findall('item')
    removed = []
    for item in items:
        if not is_landing_page(item):
            continue
        removed.append(clean(item.findtext('title')))
        channel.remove(item)

    tree.write(NEWS_FILE, encoding='utf-8', xml_declaration=True)
    print(f'Removed {len(removed)} generic publisher landing-page item(s).')
    for title in removed[:8]:
        print(f'  landing page: {title}')


if __name__ == '__main__':
    main()
