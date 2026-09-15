#!/usr/bin/env python3
from pathlib import Path
import tempfile,xml.etree.ElementTree as ET,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import v52_postprocess as pp
import apply_feedback_pools as fp

def feed(rows):
    root=ET.Element('rss');ch=ET.SubElement(root,'channel')
    for cat,title,source,url in rows:
        i=ET.SubElement(ch,'item')
        for k,v in [('category',cat),('title',title),('source',source),('link',url),('description',title)]:ET.SubElement(i,k).text=v
    return ET.ElementTree(root)

rows=[
('world','Indiana football veterans ruled ineligible','Yahoo Sports','https://a/1'),
('world','Germany weighs AI safety regulation','Reuters','https://a/2'),
('nm','OU football vs New Mexico preview','Yahoo Sports','https://a/3'),
('gaming','Fantasy drinking party game with D&D rules','IGN','https://a/4'),
('gaming','Arc Raiders update changes progression system','PC Gamer','https://a/5'),
('technology','Apple releases iOS 27 with Siri AI overhaul','The Verge','https://a/6'),
('technology','Apple releases iOS 27 with Siri AI overhaul today','Ars Technica','https://a/7'),
('legislation','Federal bill analysis','Associated Press','https://a/8'),
('legislation','H.R. 100 - Congress.gov','Congress.gov','https://www.congress.gov/bill/100'),
]
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'News';feed(rows).write(p,encoding='utf-8',xml_declaration=True);pp.process(p)
    out=ET.parse(p).getroot().findall('.//item');titles=[x.findtext('title') for x in out];cats=[x.findtext('category') for x in out]
    assert 'Indiana football veterans ruled ineligible' not in titles
    assert 'OU football vs New Mexico preview' not in titles
    assert 'Fantasy drinking party game with D&D rules' not in titles
    assert 'Arc Raiders update changes progression system' in titles
    assert 'Federal bill analysis' not in titles
    assert 'H.R. 100 - Congress.gov' in titles
    assert sum('Apple releases iOS 27' in t for t in titles)==1

item={'title':'Apple releases iOS 27 - The Verge','title_key':fp.canonical_title('Apple releases iOS 27 - The Verge'),'source':'The Verge','source_key':fp.canonical_source('The Verge'),'url':'https://example.com/story?utm_source=x','url_key':fp.normalize_url('https://example.com/story?utm_source=x'),'category':'technology'}
d={'title':'Apple releases iOS 27 - theverge.com','source':'theverge.com','url':'https://example.com/story?utm_campaign=y','category':'gaming'}
assert fp.same_article(item,d,require_category=False)
assert not fp.same_article(item,d,require_category=True)
print('V5.2 routing + D Pool regressions passed')
