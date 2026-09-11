#!/usr/bin/env python3
"""Keep the Legislation tab limited to official legislative/action records.

Journalism belongs only in relatedArticles as supporting coverage. This guard runs
post-collection/enrichment so a sparse official fetch can never leave standalone
news stories in the Legislation pool.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

NEWS = Path('News')
OFFICIAL_SOURCE_TOKENS = (
    'congress.gov', 'congress gov', 'federal register', 'federalregister.gov',
    'white house', 'whitehouse.gov', 'new mexico legislature', 'nmlegis.gov',
    'governor of new mexico', 'farmington nm', 'san juan county',
)


def clean(value):
    value = html.unescape(value or '')
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def is_official(item):
    source = clean(item.findtext('source')).lower()
    official = clean(item.findtext('officialSource'))
    link = clean(item.findtext('link'))
    if official:
        return True
    if any(token in source for token in OFFICIAL_SOURCE_TOKENS):
        el = item.find('officialSource')
        if el is None:
            el = ET.SubElement(item, 'officialSource')
        el.text = link
        return True
    return False


def main():
    if not NEWS.exists():
        raise SystemExit('News feed not found')
    tree = ET.parse(NEWS)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')

    legislation = [x for x in channel.findall('item') if clean(x.findtext('category')) == 'legislation']
    removed = 0
    for item in legislation:
        if not is_official(item):
            channel.remove(item)
            removed += 1

    # Remove exact duplicate official records by canonical official URL/bill number.
    seen = set()
    deduped = 0
    for item in list(channel.findall('item')):
        if clean(item.findtext('category')) != 'legislation':
            continue
        key = (
            clean(item.findtext('officialSource')).lower()
            or clean(item.findtext('billNumber')).lower()
            or clean(item.findtext('link')).lower()
        )
        if not key or key in seen:
            channel.remove(item)
            deduped += 1
            continue
        seen.add(key)

    remaining = sum(1 for x in channel.findall('item') if clean(x.findtext('category')) == 'legislation')
    tree.write(NEWS, encoding='utf-8', xml_declaration=True)
    print(f'Official-only legislation guard: removed {removed} news card(s), {deduped} duplicate record(s); {remaining} official record(s) remain.')


if __name__ == '__main__':
    main()
