#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_feed as vf


def item(title, category='us', source='Reuters', desc=''):
    el=ET.Element('item')
    ET.SubElement(el,'title').text=title
    ET.SubElement(el,'description').text=desc or title
    ET.SubElement(el,'source').text=source
    ET.SubElement(el,'category').text=category
    ET.SubElement(el,'pubDate').text='Thu, 10 Sep 2026 18:00:00 GMT'
    ET.SubElement(el,'link').text='https://example.com/'+str(abs(hash((title,source))))
    return el


def main():
    # Known production regression: same $5,000 event must collapse.
    a=item("Trump offers $5,000 to every American if Republicans win midterm elections")
    b=item("Trump promised $5,000 checks if Republicans win the midterms. How would that work?",source='PBS')
    c=item("At RNC midterm convention, Trump pitches $5,000 payments to U.S. citizens — but only if GOP wins House and Senate",source='NBC News')
    assert vf.same_event(a,b), 'Known $5,000 duplicate pair was missed'
    assert vf.same_event(a,c), 'Known $5,000 duplicate pair was missed'

    # Broad sports language must not join unrelated regional events.
    football_a=item('Week 2: Thursday Louisiana high school football scores and highlights','region','Yahoo Sports')
    football_b=item('Arkansas vs. Utah prediction, what to watch for College Football Week 2','region','USA Today')
    football_c=item('Wisconsin high school football scores, updates | Week 4','region','Yahoo Sports')
    assert not vf.same_event(football_a,football_b), 'Unrelated regional football stories were merged'
    assert not vf.same_event(football_a,football_c), 'Different-state football score stories were merged'

    # Same state-centered court/map event should still collapse.
    map_a=item('Missouri is poised to revert to former congressional districts after court rejects Trump-backed map','region','AP News')
    map_b=item('Supreme Court blocks Missouri from using new map favoring GOP in midterm elections','region','CBS News')
    assert vf.same_event(map_a,map_b), 'Same Missouri map event was not clustered'

    # Same convention is not automatically the same story/event.
    rnc_a=item('RNC convention attendees reflect on voting, unity','region','CBS News')
    rnc_b=item("New Mexico’s 2nd Congressional District race gains national attention at RNC midterm convention",'region','KRQE')
    rnc_c=item('2 arrested as protesters march near RNC midterm convention','region','NBC News')
    assert not vf.same_event(rnc_a,rnc_b), 'Different RNC convention stories were over-clustered'
    assert not vf.same_event(rnc_a,rnc_c), 'Convention and protest stories were over-clustered'

    # Years must never become numeric event fingerprints.
    year_a=item('Budget outlook for 2026 changes after new forecast')
    year_b=item('Election planning for 2026 continues in several states')
    assert 'num:2026' not in vf.amount_keys(year_a)
    assert not (vf.amount_keys(year_a)&vf.amount_keys(year_b)), 'Year was treated as event amount'

    print('verify_feed regression tests passed')


if __name__=='__main__':
    main()
