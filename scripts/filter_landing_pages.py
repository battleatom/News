import re
import xml.etree.ElementTree as ET
from pathlib import Path

NEWS_FILE = Path('News')

US_STATE_NAMES = (
    'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia',
    'Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts',
    'Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey',
    'New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island',
    'South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia',
    'Wisconsin','Wyoming','District of Columbia','Washington, D.C.','Washington DC',
)
STATE_ALT = '|'.join(re.escape(name) for name in US_STATE_NAMES)

# Only remove titles that are themselves generic publisher/state/promotional landing pages.
# Do not match a real article merely because the publisher appends a phrase such
# as "ABC News - Breaking News, Latest News and Videos" to the article title.
LANDING_PATTERNS = (
    re.compile(rf'^(?:{STATE_ALT})\s+-\s+(?:ABC|CBS|NBC|FOX) News\s+-\s+Breaking News,\s*Latest News(?: and Videos)?$', re.I),
    re.compile(r'^(?:ABC|CBS|NBC|FOX) News\s+-\s+Breaking News,\s*Latest News(?: and Videos)?$', re.I),
    re.compile(rf'^(?:{STATE_ALT})\s+-\s+(?:ABC|CBS|NBC|FOX) News\s+-\s+Latest News,\s*Weather(?:\s*(?:and|&)\s*Sports)?$', re.I),
    # ESPN occasionally exposes its product/streaming landing page through Google
    # News. This is navigation/marketing, not a reported news article.
    re.compile(r'^Watch ESPN\s*-\s*Stream Live Sports(?:\s*&\s*ESPN Originals)?$', re.I),
)


def clean(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip()


def is_landing_page(item) -> bool:
    title = clean(item.findtext('title'))
    if not title:
        return True
    return any(pattern.fullmatch(title) for pattern in LANDING_PATTERNS)


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
