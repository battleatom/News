import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.refine_tech_gaming import (
    gaming_allowed, tech_relevance_decision, tech_cluster_score, text, us_route
)


def item(title, category='us', description='', source='Test Source'):
    x=ET.Element('item')
    ET.SubElement(x,'title').text=title
    ET.SubElement(x,'category').text=category
    ET.SubElement(x,'description').text=description or title
    ET.SubElement(x,'source').text=source
    ET.SubElement(x,'link').text='https://example.com/story'
    ET.SubElement(x,'pubDate').text='Mon, 14 Sep 2026 12:00:00 +0000'
    return x


# Screenshot regressions.
assert us_route(item('US embassy child abuse images suspect flown from UK before police interview - BBC', description='The individual worked at the US embassy in Vauxhall, south London.')) == 'world'
assert us_route(item("How Trump’s Proposed Census Changes Could Impact States’ Funding—and Political Power")) == 'presidential'
assert not gaming_allowed(item('Hobby Beacon tabletop gaming store to offer 40K minis, card packs and more in Lincoln', category='gaming'))
assert gaming_allowed(item('Sony announces major PlayStation 5 game release for October', category='gaming', source='IGN'))
assert tech_relevance_decision(item('OpenAI launches new AI model for developers', category='technology', source='The Verge')) == 'technology'

weak=item('Israeli AI maritime tech company joins Virginia Beach incubator', category='technology', description='The local incubator announced the company is exploring partnerships and pilot programs.', source='The Virginian-Pilot')
score,coverage,_=tech_cluster_score([weak])
assert score < 40, f'low-impact single-source incubator story should not rank in Technology: {score}'

# When run after the live refinement step, validate the actual feed too.
news=Path('News')
if news.exists():
    items=ET.parse(news).getroot().findall('./channel/item')
    groups={cat:[x for x in items if text(x,'category')==cat] for cat in ('technology','gaming','us')}
    assert len(groups['technology']) >= 10, f"Technology too small: {len(groups['technology'])}"
    assert len(groups['gaming']) >= 8, f"Gaming too small: {len(groups['gaming'])}"
    assert len(groups['us']) >= 8, f"US too small: {len(groups['us'])}"
    for x in groups['gaming']:
        t=(text(x,'title')+' '+text(x,'description')).lower()
        assert not any(w in t for w in ('tabletop','hobby store','gaming store','card packs','miniatures')), text(x,'title')
    toptech=' '.join(text(x,'title').lower() for x in groups['technology'][:5])
    assert 'incubator' not in toptech, toptech
    for x in groups['us']:
        t=text(x,'title').lower()
        assert not ('embassy' in t and any(p in t for p in ('london','uk','britain'))), text(x,'title')

print('TOPIC QUALITY REGRESSION PASS')
