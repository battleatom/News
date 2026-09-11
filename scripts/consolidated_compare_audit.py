from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_NEWS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "baseline-News"
BASE_INDEX = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "baseline-index.html"
CAND_NEWS = ROOT / "News"
CAND_INDEX = ROOT / "index.html"
OUT_JSON = ROOT / "consolidated-audit.json"
OUT_MD = ROOT / "consolidated-audit.md"

EXPECTED_TABS = ['top','nfl','x','underreported','world','us','presidential','federal','legislation','nm','local','region','technology','gaming','military','boxoffice']
FOREIGN = ('sweden','brazil','russia','ukraine','china','iran','israel','gaza','france','germany','mexico','canada','britain','united kingdom','japan','india','nato','united nations')
US_FED = ('white house','congress','senate','house of representatives','scotus','u.s. supreme court','department of justice','doj','fbi','federal reserve','irs','pentagon')
NFL = ('nfl','super bowl','quarterback','touchdown','national football league','chiefs','cowboys','broncos','49ers','packers','steelers','eagles','ravens','bills','patriots')
NON_NFL_SPORT = ('tennis',' atp ',' wta ','soccer','mlb','baseball','nba','basketball','nhl','hockey','golf','pga','formula 1',' f1 ')
TECH = ('artificial intelligence',' ai ','openai','chatgpt','cybersecurity','software','semiconductor','nvidia','amd','intel','microsoft','google','apple','robotics','quantum','cloud computing')
GAMING = ('video game','gaming','playstation','xbox','nintendo','steam','game studio','console','pc gamer','gamespot','ign')
MILITARY = ('military','pentagon','troops','armed forces','air force','army','navy','marines','missile','airstrike','defense department')
PRESIDENTIAL = ('president trump','donald trump','white house','executive order','presidential','administration')
NM = ('new mexico','albuquerque','santa fe','nm legislature')
LOCAL = ('farmington','san juan county','aztec','bloomfield','kirtland','shiprock','four corners','durango','la plata county','cortez','montezuma county','navajo nation','gallup')


def clean(v: str | None) -> str:
    return re.sub(r'\s+', ' ', v or '').strip()


def parse_feed(path: Path):
    root = ET.parse(path).getroot()
    rows = []
    for i in root.findall('./channel/item'):
        rows.append({
            'title': clean(i.findtext('title')),
            'source': clean(i.findtext('source')),
            'category': clean(i.findtext('category')).lower() or 'world',
            'link': clean(i.findtext('link')),
            'description': clean(i.findtext('description')),
            'officialSource': clean(i.findtext('officialSource')),
            'billNumber': clean(i.findtext('billNumber')),
        })
    return rows


def tabs(html: str):
    return [t for t in EXPECTED_TABS if re.search(rf"\['{re.escape(t)}'\s*,", html)]


def contains_any(text: str, terms) -> bool:
    padded = f" {text.lower()} "
    return any(term in padded for term in terms)


def suspicious(row):
    text = f"{row['title']} {row['description']}".lower()
    cat = row['category']
    reasons = []
    if cat == 'federal' and contains_any(text, FOREIGN) and not contains_any(text, US_FED):
        reasons.append('foreign-focused story in federal')
    if cat in {'world','federal'} and contains_any(text, NON_NFL_SPORT):
        reasons.append(f'non-NFL sports story routed to {cat}')
    if cat == 'nfl' and not contains_any(text, NFL):
        reasons.append('weak NFL signal')
    if cat == 'technology' and not contains_any(text, TECH):
        reasons.append('weak technology signal')
    if cat == 'gaming' and not contains_any(text, GAMING):
        reasons.append('weak gaming signal')
    if cat == 'military' and not contains_any(text, MILITARY):
        reasons.append('weak military signal')
    if cat == 'presidential' and not contains_any(text, PRESIDENTIAL):
        reasons.append('weak presidential signal')
    if cat == 'nm' and not contains_any(text, NM):
        reasons.append('weak New Mexico signal')
    if cat == 'local' and not contains_any(text, LOCAL):
        reasons.append('weak local-area signal')
    if cat == 'legislation' and not (row['officialSource'] or row['billNumber'] or 'congress.gov' in row['link'] or 'nmlegis.gov' in row['link'] or 'federalregister.gov' in row['link']):
        reasons.append('legislation card lacks clear official-record marker')
    if not row['title'] or not row['link'] or not row['source']:
        reasons.append('missing required article field')
    return reasons


def summarize(rows):
    counts = Counter(r['category'] for r in rows)
    same_cat = Counter((r['category'], r['link']) for r in rows if r['link'])
    within_category_dups = [{'category':cat,'link':link,'count':n} for (cat,link),n in same_cat.items() if n > 1]
    link_cats = defaultdict(set)
    for r in rows:
        if r['link']:
            link_cats[r['link']].add(r['category'])
    cross_category_dups = [{'link':link,'categories':sorted(cats)} for link,cats in link_cats.items() if len(cats) > 1]
    flagged = []
    for n,row in enumerate(rows,1):
        rs = suspicious(row)
        if rs:
            flagged.append({'index':n, **row, 'reasons':rs})
    return {
        'total':len(rows),
        'counts':dict(sorted(counts.items())),
        'withinCategoryDuplicateLinks':within_category_dups,
        'crossCategoryDuplicateLinks':cross_category_dups,
        'flagged':flagged,
    }


def main():
    base = parse_feed(BASE_NEWS)
    cand = parse_feed(CAND_NEWS)
    base_html = BASE_INDEX.read_text(encoding='utf-8')
    cand_html = CAND_INDEX.read_text(encoding='utf-8')
    bsum, csum = summarize(base), summarize(cand)
    base_links = {r['link']:r for r in base if r['link']}
    cand_links = {r['link']:r for r in cand if r['link']}
    added = [cand_links[k] for k in cand_links.keys()-base_links.keys()]
    removed = [base_links[k] for k in base_links.keys()-cand_links.keys()]
    recategorized = []
    for k in base_links.keys() & cand_links.keys():
        if base_links[k]['category'] != cand_links[k]['category']:
            recategorized.append({'link':k,'title':cand_links[k]['title'],'from':base_links[k]['category'],'to':cand_links[k]['category']})
    report = {
        'baseline': bsum,
        'candidate': csum,
        'tabs': {'baseline':tabs(base_html),'candidate':tabs(cand_html),'missingCandidate':[t for t in EXPECTED_TABS if t not in tabs(cand_html)]},
        'delta': {'added':added,'removed':removed,'recategorized':recategorized},
        'candidateArticles': cand,
    }
    OUT_JSON.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines = [
        '# Consolidated build audit','',
        f"Baseline articles: **{len(base)}**  ",
        f"Candidate articles: **{len(cand)}**  ",
        f"Candidate routing/content flags: **{len(csum['flagged'])}**  ",
        f"Within-category exact duplicate links: **{len(csum['withinCategoryDuplicateLinks'])}**  ",
        f"Intentional/possible cross-category repeated links: **{len(csum['crossCategoryDuplicateLinks'])}**",
        '', '## Category counts',''
    ]
    cats = sorted(set(bsum['counts'])|set(csum['counts']))
    lines += ['| Category | Baseline | Candidate |','|---|---:|---:|'] + [f"| {c} | {bsum['counts'].get(c,0)} | {csum['counts'].get(c,0)} |" for c in cats]
    lines += ['', '## Tabs', '', f"Baseline: {', '.join(report['tabs']['baseline'])}", '', f"Candidate: {', '.join(report['tabs']['candidate'])}", '', '## Routing/content flags', '']
    if csum['flagged']:
        for f in csum['flagged']:
            lines.append(f"- [{f['category']}] {f['title']} — {', '.join(f['reasons'])}")
    else:
        lines.append('- None detected by the consolidated routing/content audit.')
    lines += ['', '## Every candidate article', '']
    for n,r in enumerate(cand,1):
        lines.append(f"{n}. **[{r['category']}] {r['title']}** — {r['source']} — {r['link']}")
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({
        'baselineTotal':len(base),
        'candidateTotal':len(cand),
        'flags':len(csum['flagged']),
        'withinCategoryDuplicates':len(csum['withinCategoryDuplicateLinks']),
        'crossCategoryRepeatedLinks':len(csum['crossCategoryDuplicateLinks']),
        'added':len(added),
        'removed':len(removed),
        'recategorized':len(recategorized),
        'missingTabs':report['tabs']['missingCandidate']
    }, indent=2))
    if csum['withinCategoryDuplicateLinks'] or report['tabs']['missingCandidate']:
        raise SystemExit('Consolidated audit failed hard integrity checks.')


if __name__ == '__main__':
    main()
