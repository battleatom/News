#!/usr/bin/env python3
import importlib.util
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('tabq',ROOT/'scripts/enforce_tab_quality_v5.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def item(cat,title,desc='',resolved=''):
    x=ET.Element('item')
    for tag,val in [('title',title),('description',desc),('category',cat),('source','Reuters'),('link','https://example.com/'+str(abs(hash(title)))),('pubDate','Sat, 12 Sep 2026 12:00:00 GMT')]:
        ET.SubElement(x,tag).text=val
    if resolved:ET.SubElement(x,'resolvedPublisherUrl').text=resolved
    return x

wy=item('us','Wyoming holds on to beat Indian Hill in triple-overtime CHL thriller','The teams traded punches for four quarters and three overtimes in Week 4.')
assert m.apply_rule(wy)==('drop',None,'ordinary-sports-in-us')
nfl=item('us','Chiefs rally late to beat Chargers','Kansas City won the NFL game.')
assert m.apply_rule(nfl)==('reroute','nfl','ordinary-sports-to-nfl')
policy=item('us','Congress examines NCAA antitrust rules affecting college football','Lawmakers considered federal policy changes.')
assert m.apply_rule(policy)[0]=='keep'
gaga=item('world','Lady Gaga Welcomes First Child With Fiancé Michael Polansky','International reporting indicates The Grammy and Oscar winner welcomed her first child.')
assert m.apply_rule(gaga)==('drop',None,'domestic-entertainment-in-world')
cia=item('world','Declassified CIA documents show clear warnings to presidents before 9/11','International reporting indicates CIA records describe warnings before September 11.')
assert m.apply_rule(cia)==('reroute','federal','domestic-federal-in-world')
rap=item('world','US rapper Lil Durk found not guilty of murder-for-hire scheme','International reporting indicates U.S. prosecutors accused the rapper in a domestic criminal case.')
assert m.apply_rule(rap)[0] in {'drop','reroute'}
baseball=item('world','World Baseball League to host Field of Dreams Festival','International reporting indicates The baseball league will host a three-day festival in Iowa.')
assert m.apply_rule(baseball)==('drop',None,'ordinary-sports-in-world')
brics=item('world','BRICS summit weighs Iran war and global economic challenges','International reporting indicates India, Russia and China discussed diplomacy and sanctions.')
assert m.apply_rule(brics)[0]=='keep'
icc=item('world','As Trump squeezes the International Criminal Court, more countries are leaving','International reporting indicates the international tribunal faces pressure as member states reconsider participation.')
assert m.apply_rule(icc)[0]=='keep'
review=item('gaming','Undercover Cops Review for Arcade Games: I Forget These Are Cops - GameFAQs','A review of the arcade game.','https://gamefaqs.gamespot.com/arcade/567405-undercover-cops/reviews/179974')
assert m.apply_rule(review)==('drop',None,'gaming-non-news-content')
blizz=item('gaming','BlizzCon 2026 Opening Ceremony: Start Time, How To Watch, And What To Expect','BlizzCon opens with current announcements and a showcase.')
assert m.apply_rule(blizz)[0]=='keep'
root=ET.Element('rss');channel=ET.SubElement(root,'channel')
fixtures=[wy,nfl,policy,gaga,cia,brics,icc,review,blizz]
for x in fixtures:channel.append(x)
with tempfile.TemporaryDirectory() as td:
    feed=Path(td)/'News';report=Path(td)/'report.json';ET.ElementTree(root).write(feed,encoding='utf-8',xml_declaration=True)
    out=m.run(feed,report,True)
    assert out['actions'] and report.exists()
    cats=[(i.findtext('category') or '') for i in ET.parse(feed).getroot().findall('.//item')]
    assert 'nfl' in cats and 'federal' in cats
    types=[(i.findtext('articleType') or '') for i in ET.parse(feed).getroot().findall('.//item')]
    assert all(types)
print('V5 tab quality test passed.')
