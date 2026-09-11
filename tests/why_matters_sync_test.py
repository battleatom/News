#!/usr/bin/env python3
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sync',ROOT/'scripts'/'sync_why_matters.py')
sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'News'
    rss=ET.Element('rss');channel=ET.SubElement(rss,'channel')
    item=ET.SubElement(channel,'item')
    for tag,val in [('title','Court ruling changes ballot rules - Test Source'),('description','U.S. reporting indicates a court ruling changes how ballots are handled in the upcoming election.'),('source','Test Source'),('category','us'),('briefGenerated','true'),('whyMatters','old generic text')]:
        ET.SubElement(item,tag).text=val
    ET.ElementTree(rss).write(p,encoding='utf-8',xml_declaration=True)
    sync.NEWS=p;sync.main()
    out=ET.parse(p).getroot().find('.//item')
    why=out.findtext('whyMatters') or ''
    assert why.startswith('Why it matters:'),why
    assert 'elections' in why or 'legal rights' in why,why
    assert out.findtext('whyMattersSource')=='content-brief-v1'

print('Why It Matters sync test passed.')
