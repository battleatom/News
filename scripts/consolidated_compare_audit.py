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
NFL = ('nfl','super bowl','quarterback','touchdown','national football league')
NON_NFL_SPORT = ('tennis','atp','wta','soccer','mlb','baseball','nba','basketball','nhl','hockey','golf','pga','formula 1','f1')


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


def suspicious(row):
    text = f"{row['title']} {row['description']}".lower()
    cat = row['category']
    reasons = []
    if cat == 'federal' and any(x in text for x in FOREIGN) and not any(x in text for x in US_FED):
        reasons.append('foreign-focused story in federal')
    if cat == 'world' and any(x in text for x in NON_NFL_SPORT):
        reasons.append('non-NFL sports story routed to world')
    if cat == 'federal' and any(x in text for x in NON_NFL_SPORT):
        reasons.append('sports story routed to federal')
    if cat == 'nfl' and not any(x in text for x in NFL):
        reasons.append('weak NFL signal')
    if cat == 'legislation' and not (row['officialSource'] or row['billNumber'] or 'congress.gov' in row['link'] or 'nmlegis.gov' in row['link'] or 'federalregister.gov' in row['link']):
        reasons.append('legislation card lacks clear official-record marker')
    if not row['title'] or not row['link'] or not row['source']:
        reasons.append('missing required article field')
    return reasons


def summarize(rows):
    counts = Counter(r['category'] for r in rows)
    links = Counter(r['link'] for r in rows if r['link'])
    exact_dups = [link for link,n in links.items() if n > 1]
    flagged = []
    for n,row in enumerate(rows,1):
        rs = suspicious(row)
        if rs:
            flagged.append({'index':n, **row, 'reasons':rs})
    return {'total':len(rows),'counts':dict(sorted(counts.items())),'exactDuplicateLinks':exact_dups,'flagged':flagged}


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
    lines = ['# Consolidated build audit','',f"Baseline articles: **{len(base)}**  ",f"Candidate articles: **{len(cand)}**  ",f"Candidate routing flags: **{len(csum['flagged'])}**  ",f"Candidate exact duplicate links: **{len(csum['exactDuplicateLinks'])}**",'', '## Category counts','']
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
    print(json.dumps({'baselineTotal':len(base),'candidateTotal':len(cand),'flags':len(csum['flagged']),'duplicates':len(csum['exactDuplicateLinks']),'added':len(added),'removed':len(removed),'recategorized':len(recategorized),'missingTabs':report['tabs']['missingCandidate']}, indent=2))
    if csum['exactDuplicateLinks'] or report['tabs']['missingCandidate']:
        raise SystemExit('Consolidated audit failed hard integrity checks.')


if __name__ == '__main__':
    main()
