#!/usr/bin/env python3
import copy, importlib.util, json, tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('guard',ROOT/'scripts'/'quality_guard_v4.py')
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def item(title,cat,desc='',source='Test',state='',topic=''):
    n=ET.Element('item')
    for k,v in [('title',title),('link','https://example.com/'+str(abs(hash(title)))),('description',desc),('source',source),('category',cat),('state',state),('xTopic',topic)]:
        e=ET.SubElement(n,k); e.text=v
    return n

world=item('How to watch Howard vs Indiana: College football live stream','world','College football game in Indiana','Yahoo Sports','Indiana')
can=item('Lack of space keeping federal public servants from more office time','federal','Canadian federal public servants in Ottawa','CBC')
items=[world,can]
assert g.reroute(items)==2
assert g.txt(world,'category')=='us'
assert g.txt(can,'category')=='world'

p=item('CIA declassifies intel warnings prior to 9/11 attack','top')
r=ET.SubElement(p,'relatedArticles')
for t in ['White House launches Tetris-style Build the Wall game','CIA releases new 9/11 intelligence warning files']:
    a=ET.SubElement(r,'article'); ET.SubElement(a,'title').text=t
removed=g.clean_related([p])
assert removed==1, removed
assert len(r.findall('article'))==1

f=item('Election Rights & Troops At Elections','legislation')
ET.SubElement(f,'briefSource').text='headline-fallback'
ET.SubElement(f,'rssDescription').text='New Mexico lawmakers approved changes governing election rights and the use of troops around polling places after debate over election administration.'
ET.SubElement(f,'whyMatters').text='Why it matters: This could change the military or diplomatic situation, affect regional security, or increase the risk of further escalation.'
up,why=g.final_enhance([f])
assert up==1 and g.txt(f,'briefSource')=='rss-description'
assert why==1 and 'laws, funding' in g.txt(f,'whyMatters')

with tempfile.TemporaryDirectory() as td:
    old=g.BOX; g.BOX=Path(td)/'boxoffice.json'
    g.BOX.write_text(json.dumps({'movies':[{'title':'Runner','description':'Running is a method of terrestrial locomotion by which humans and other animals move quickly on foot. '+'x'*220}]}),encoding='utf-8')
    assert g.clean_boxoffice()==1
    assert json.loads(g.BOX.read_text())['movies'][0]['description']==''
    g.BOX=old

print('quality_guard_v4 regression tests passed')
