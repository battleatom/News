#!/usr/bin/env python3
import importlib.util
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('guard', ROOT / 'scripts' / 'enforce_official_legislation.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def add_item(channel, title, source, category='legislation', link='https://example.com/item', official=''):
    item = ET.SubElement(channel, 'item')
    for tag, value in [('title', title), ('source', source), ('category', category), ('link', link)]:
        ET.SubElement(item, tag).text = value
    if official:
        ET.SubElement(item, 'officialSource').text = official
    return item


with tempfile.TemporaryDirectory() as td:
    path = Path(td) / 'News'
    rss = ET.Element('rss')
    channel = ET.SubElement(rss, 'channel')
    add_item(channel, 'H.R. 1 — Official bill', 'Congress.gov', link='https://www.congress.gov/bill/119th-congress/house-bill/1')
    add_item(channel, 'Journalism about a bill', 'Reuters', link='https://reuters.com/story')
    add_item(channel, 'SB 20 — State bill', 'New Mexico Legislature', link='https://www.nmlegis.gov/Legislation/Legislation?Chamber=S&LegNo=20&LegType=B&year=26')
    add_item(channel, 'Official with metadata', 'Unknown label', link='https://official.example/record', official='https://official.example/record')
    add_item(channel, 'Normal technology story', 'Reuters', category='technology', link='https://reuters.com/tech')
    ET.ElementTree(rss).write(path, encoding='utf-8', xml_declaration=True)

    guard.NEWS = path
    guard.main()

    out = ET.parse(path).getroot().find('channel')
    legislation = [x for x in out.findall('item') if guard.clean(x.findtext('category')) == 'legislation']
    titles = [guard.clean(x.findtext('title')) for x in legislation]
    assert 'Journalism about a bill' not in titles, titles
    assert len(legislation) == 3, titles
    assert all(guard.clean(x.findtext('officialSource')) for x in legislation), titles
    assert any(guard.clean(x.findtext('category')) == 'technology' for x in out.findall('item'))

print('Official legislation guard tests passed.')
