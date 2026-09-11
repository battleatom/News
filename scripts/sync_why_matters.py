#!/usr/bin/env python3
"""Regenerate Why It Matters after the paraphrase/content-brief pass.

Only article cards with briefGenerated=true are updated. The impact sentence is derived
from the freshly paraphrased description plus headline/category, so Why It Matters cannot
silently drift away from the brief shown on the card.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

NEWS = Path('News')

IMPACTS = [
    (('election','vote','voting','ballot','campaign','midterm'), 'elections, representation, or how voters and campaigns operate'),
    (('court','judge','ruling','appeal','lawsuit','legal','supreme court'), 'legal rights, court precedent, or how government authority is applied'),
    (('war','military','missile','strike','troops','ceasefire','defense'), 'security, military operations, diplomacy, or the risk of further escalation'),
    (('economy','inflation','jobs','wage','tariff','price','market','recession'), 'household costs, jobs, business conditions, or the broader economy'),
    (('health','medicaid','medicare','hospital','drug','outbreak','insurance'), 'health access, medical costs, public-health policy, or patient care'),
    (('school','student','teacher','college','education'), 'students, schools, families, or education policy'),
    (('privacy','surveillance','cyber','breach','hack','data'), 'privacy, cybersecurity, personal data, or digital safety'),
    (('ai','artificial intelligence','software','technology','chip','semiconductor'), 'technology policy, products, competition, or how people use digital systems'),
    (('immigration','border','migrant','asylum','visa','deport'), 'immigration policy, border operations, or people navigating the immigration system'),
    (('climate','wildfire','water','environment','energy','pollution','storm','flood'), 'public safety, infrastructure, energy, or environmental conditions'),
    (('crime','police','arrest','murder','shooting','indict'), 'public safety, law enforcement, criminal justice, or affected communities'),
    (('nfl','football','quarterback','playoff','touchdown'), 'teams, players, standings, scheduling, or the competitive season'),
    (('gaming','game','playstation','xbox','nintendo','steam'), 'players, platforms, publishers, releases, or the games market'),
]

CATEGORY_FALLBACK = {
    'world':'international policy, security, economies, or people affected across borders',
    'us':'U.S. policy, institutions, communities, or household conditions',
    'presidential':'White House policy, executive action, federal priorities, or public administration',
    'federal':'federal policy, agencies, public programs, rights, or government operations',
    'nm':'New Mexico residents, state policy, public services, or the regional economy',
    'local':'local residents, public services, schools, businesses, or community safety',
    'region':'people, governments, infrastructure, or economies across the affected region',
    'technology':'technology users, companies, regulation, competition, or digital systems',
    'gaming':'players, platforms, publishers, releases, or the games industry',
    'military':'security, military operations, diplomacy, or service members and civilians',
    'nfl':'teams, players, standings, scheduling, or the competitive season',
    'underreported':'people, institutions, policy, costs, safety, or rights connected to the issue',
    'top':'people, institutions, policy, costs, safety, or rights connected to the development',
}


def clean(v):
    return re.sub(r'\s+', ' ', (v or '')).strip()


def has_term(text, term):
    return re.search(r'(?<![a-z0-9])' + re.escape(term.lower()) + r'(?![a-z0-9])', text.lower()) is not None


def set_text(item, tag, value):
    node=item.find(tag)
    if node is None:
        node=ET.SubElement(item,tag)
    node.text=value


def impact_for(text, category):
    for terms, impact in IMPACTS:
        if any(has_term(text, term) for term in terms):
            return impact
    return CATEGORY_FALLBACK.get(category, 'people, institutions, policy, costs, safety, or rights connected to the development')


def build_why(item):
    title=clean(item.findtext('title'))
    desc=clean(item.findtext('description'))
    category=clean(item.findtext('category')).lower()
    source=clean(item.findtext('source'))
    if source:
        title=re.sub(rf'\s*[-–—|:]\s*{re.escape(source)}\s*$', '', title, flags=re.I).strip()
    context=f'{title} {desc}'
    impact=impact_for(context,category)
    subject=title
    if len(subject)>145:
        subject=subject[:142].rsplit(' ',1)[0]+'…'
    return f'Why it matters: The reporting on {subject} could affect {impact}. The assessment is tied to the paraphrased article brief shown above, not just the headline.'


def main():
    tree=ET.parse(NEWS)
    changed=0
    for item in tree.getroot().findall('.//item'):
        if clean(item.findtext('category')).lower()=='legislation':
            continue
        if clean(item.findtext('briefGenerated')).lower()!='true':
            continue
        if not clean(item.findtext('description')):
            continue
        set_text(item,'whyMatters',build_why(item))
        set_text(item,'whyMattersSource','content-brief-v1')
        changed+=1
    tree.write(NEWS,encoding='utf-8',xml_declaration=True)
    print(f'Why It Matters sync: {changed} card(s) regenerated from paraphrased content briefs.')


if __name__=='__main__':
    main()
