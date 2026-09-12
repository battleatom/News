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
MONTH_ALT = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'

# This filter is intentionally title-shape based instead of using a word-count
# minimum. Short event headlines such as "Russia destroys hospital" are valid news;
# station/program pages and dated roundup episodes are not specific news events.
LANDING_PATTERNS = (
    re.compile(rf'^(?:{STATE_ALT})\s+-\s+(?:ABC|CBS|NBC|FOX) News\s+-\s+Breaking News,\s*Latest News(?: and Videos)?$', re.I),
    re.compile(r'^(?:ABC|CBS|NBC|FOX) News\s+-\s+Breaking News,\s*Latest News(?: and Videos)?$', re.I),
    re.compile(rf'^(?:{STATE_ALT})\s+-\s+(?:ABC|CBS|NBC|FOX) News\s+-\s+Latest News,\s*Weather(?:\s*(?:and|&)\s*Sports)?$', re.I),
    # ESPN occasionally exposes its product/streaming landing page through Google
    # News. This is navigation/marketing, not a reported news article.
    re.compile(r'^Watch ESPN\s*-\s*Stream Live Sports(?:\s*&\s*ESPN Originals)?$', re.I),
    # Broadcast/program listings describe a show or timeslot rather than one event.
    # Examples seen in production: "Local 10 World News @06:30 PM" and
    # "The National News Desk Weekend Edition".
    re.compile(r'^(?:Local\s+\d+\s+)?(?:World|National|Local)?\s*News\s*@\s*\d{1,2}:\d{2}\s*(?:AM|PM)$', re.I),
    re.compile(r'^(?:The\s+)?National News Desk(?:\s+Weekend Edition)?$', re.I),
    re.compile(r'^(?:The\s+)?(?:World|National|Local) News(?:\s+(?:Morning|Midday|Evening|Weekend) Edition)?$', re.I),
    # Dated roundup/show episode titles are containers for multiple stories, not a
    # single article. Keep event-specific "roundup" headlines that name a subject.
    re.compile(rf'^(?:The\s+)?News Roundup(?:\s+For)?\s+{MONTH_ALT}\s+\d{{1,2}}(?:,\s*\d{{4}})?(?:\s*[:\-–—].*)?$', re.I),
    re.compile(r'^News Roundup(?:\s+For)?\s+\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?(?:\s*[:\-–—].*)?$', re.I),
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
    print(f'Removed {len(removed)} generic publisher/program/landing-page item(s).')
    for title in removed[:8]:
        print(f'  non-story page: {title}')


if __name__ == '__main__':
    main()
