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

def max_streak(items):
    best=0;run=0;last=None
    for i in items:
        s=pp.source_id(i)
        run=run+1 if s==last else 1;last=s;best=max(best,run)
    return best

rows=[
('world','Indiana football veterans ruled ineligible','Yahoo Sports','https://a/1'),
('world','Germany weighs AI safety regulation','Reuters','https://a/2'),
('world','Major ransomware campaign hits hospitals worldwide','TechCrunch','https://a/21'),
('nm','OU football vs New Mexico preview','Yahoo Sports','https://a/3'),
('local','John Doe Obituary 1940-2026','Local Paper','https://a/31'),
('gaming','Fantasy drinking party game with D&D rules','IGN','https://a/4'),
('gaming','Arc Raiders update changes progression system','PC Gamer','https://a/5'),
('technology','Apple releases iOS 27 with Siri AI overhaul','The Verge','https://a/6'),
('technology','Apple releases iOS 27 with Siri AI overhaul today','Ars Technica','https://a/7'),
('legislation','Federal bill analysis','Associated Press','https://a/8'),
('legislation','H.R. 100 - Congress.gov','Congress.gov','https://www.congress.gov/bill/100'),
]
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'News';feed(rows).write(p,encoding='utf-8',xml_declaration=True);pp.process(p)
    out=ET.parse(p).getroot().findall('.//item');titles=[x.findtext('title') for x in out]
    assert 'Indiana football veterans ruled ineligible' not in titles
    assert 'OU football vs New Mexico preview' not in titles
    assert 'John Doe Obituary 1940-2026' not in titles
    assert 'Fantasy drinking party game with D&D rules' not in titles
    assert 'Arc Raiders update changes progression system' in titles
    assert 'Federal bill analysis' not in titles
    assert 'H.R. 100 - Congress.gov' in titles
    assert sum('Apple releases iOS 27' in t for t in titles)==1
    assert 'Major ransomware campaign hits hospitals worldwide' in titles
    tech=[x for x in out if x.findtext('category')=='technology']
    assert any('ransomware' in (x.findtext('title') or '').lower() for x in tech)

# A dominant source must be spread through the category, not dumped into a tail.
seq=[]
for n in range(12):
    i=ET.Element('item');ET.SubElement(i,'source').text='Reuters';ET.SubElement(i,'title').text=f'Reuters story {n}';seq.append(i)
for source,n in [('AP',4),('BBC',3),('NPR',3),('Guardian',2)]:
    for k in range(n):
        i=ET.Element('item');ET.SubElement(i,'source').text=source;ET.SubElement(i,'title').text=f'{source} story {k}';seq.append(i)
scheduled,dropped=pp.balanced_schedule(seq,2)
assert not dropped
assert max_streak(scheduled)<=2

# Impossible single-source overhang is dropped rather than rendered as a long block.
seq=[]
for n in range(10):
    i=ET.Element('item');ET.SubElement(i,'source').text='ESPN';ET.SubElement(i,'title').text=f'ESPN {n}';seq.append(i)
for n in range(2):
    i=ET.Element('item');ET.SubElement(i,'source').text='CBS Sports';ET.SubElement(i,'title').text=f'CBS {n}';seq.append(i)
scheduled,dropped=pp.balanced_schedule(seq,2)
assert dropped
assert max_streak(scheduled)<=2

item={'title':'Apple releases iOS 27 - The Verge','title_key':fp.canonical_title('Apple releases iOS 27 - The Verge'),'source':'The Verge','source_key':fp.canonical_source('The Verge'),'url':'https://example.com/story?utm_source=x','url_key':fp.normalize_url('https://example.com/story?utm_source=x'),'category':'technology'}
d={'title':'Apple releases iOS 27 - theverge.com','source':'theverge.com','url':'https://example.com/story?utm_campaign=y','category':'gaming'}
assert fp.same_article(item,d,require_category=False)
assert not fp.same_article(item,d,require_category=True)
print('V5.2 routing + D Pool regressions passed')
