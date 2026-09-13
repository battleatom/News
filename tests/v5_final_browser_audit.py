#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'v5-final-browser-audit.json'
V5 = 'http://127.0.0.1:8765/'
V4 = 'http://127.0.0.1:8766/'
LOCATION = {'latitude':36.7281,'longitude':-108.2187}
REQUIRED = {
    'top','nfl','x','underreported','entertainment','world','us','presidential',
    'federal','legislation','nm','technology','gaming','military','boxoffice'
}
EXPECTED_X = [
    'HEALTH','TECHNOLOGY & AI','CELEBRITIES & PUBLIC FIGURES','WORLD',
    'POLITICS & GOVERNMENT','ENTERTAINMENT','SPORTS','BUSINESS & ECONOMY',
    'GAMING','SCIENCE'
]


def norm(value):
    value = re.sub(r'^\s*\d+\s*[.)]\s*', '', value or '')
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def setup(page):
    page.add_init_script("""
      localStorage.setItem('underreported-location-v2', JSON.stringify({lat:36.7281,lon:-108.2187,city:'Farmington',state:'NM',label:'Farmington, NM',source:'audit',savedAt:9999999999999}));
      localStorage.setItem('underreported-location','Farmington, NM');
      localStorage.setItem('underreported-state','NM');
    """)


def tab_keys(page):
    return page.locator('#tabs > .tab').evaluate_all("els=>els.map(e=>e.dataset.navKey).filter(Boolean)")


def click(page, key):
    tab = page.locator(f'#tabs > .tab[data-nav-key="{key}"]')
    if tab.count() == 0:
        return False
    tab.first.click()
    page.wait_for_timeout(250)
    return True


def visible_titles(page):
    return page.locator('#news-feed article h2, #news-feed article h3, #news-feed .news-item h2, #news-feed .news-item h3').evaluate_all(
        "els=>els.map(e=>e.textContent.trim()).filter(Boolean)"
    )


def snapshot(browser, url):
    ctx = browser.new_context(viewport={'width':1440,'height':950}, geolocation=LOCATION, permissions=['geolocation'])
    page = ctx.new_page()
    setup(page)
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    page.wait_for_selector('#tabs', timeout=10000)
    page.wait_for_timeout(900)
    keys = tab_keys(page)
    data = {}
    for key in keys:
        if key == 'bookmarks' or not click(page, key):
            continue
        titles = visible_titles(page)
        clean = [norm(x) for x in titles if norm(x)]
        data[key] = {
            'count': len(titles),
            'duplicateTitles': len(clean) - len(set(clean)),
            'titles': titles[:80],
        }
    extra = {}
    if click(page, 'x'):
        extra['xTopics'] = [x.strip().upper() for x in page.locator('#news-feed .x-topic').all_inner_texts()]
        extra['xCards'] = page.locator('#news-feed .x-issue-item').count()
    if click(page, 'entertainment'):
        extra['dirtyControls'] = page.locator('.ent-mode-toggle, .ent-mode-state, .ent-broad-note').count()
    if click(page, 'nfl'):
        extra['nflCards'] = page.locator('.nfl-game-card, .nfl-game').count()
        extra['streamRows'] = page.locator('.nfl-stream').count()
    if click(page, 'nm'):
        extra['stateTab'] = page.locator('#tabs > .tab[data-nav-key="nm"]').inner_text().strip()
        extra['locationScopes'] = page.locator('.location-scope-bar .location-scope-btn').all_inner_texts() if page.locator('.location-scope-bar').count() else []
    ctx.close()
    return {'tabs':keys,'data':data,'errors':errors,'extra':extra}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        v4 = snapshot(browser, V4)
        v5 = snapshot(browser, V5)
        browser.close()

    failures = []
    missing = sorted(REQUIRED - set(v5['tabs']))
    if missing:
        failures.append(f'V5 missing required tabs: {missing}')
    if v5['errors']:
        failures.append(f"V5 browser JavaScript errors: {v5['errors'][:8]}")

    for key in sorted(REQUIRED - {'boxoffice'}):
        if v5['data'].get(key, {}).get('count', 0) == 0:
            failures.append(f'V5 required tab rendered empty: {key}')
        if v5['data'].get(key, {}).get('duplicateTitles', 0) > 0:
            failures.append(f'V5 rendered duplicate titles in: {key}')

    if v5['extra'].get('xCards') != 10:
        failures.append(f"X rendered {v5['extra'].get('xCards')} cards instead of 10")
    if v5['extra'].get('xTopics') != EXPECTED_X:
        failures.append(f"X topics/order mismatch: {v5['extra'].get('xTopics')}")
    if v5['extra'].get('dirtyControls') != 0:
        failures.append('Dirty Entertainment controls are visible on V5')
    if 'New Mexico' not in v5['extra'].get('stateTab',''):
        failures.append(f"Farmington did not resolve to New Mexico: {v5['extra'].get('stateTab')}")
    scopes = ' | '.join(v5['extra'].get('locationScopes', []))
    if scopes and ('State & County' not in scopes or 'Farmington' not in scopes or 'Southwest' not in scopes):
        failures.append(f'Farmington location scopes are incomplete: {scopes}')
    if v5['extra'].get('nflCards', 0) > 0 and v5['extra'].get('streamRows', 0) == 0:
        failures.append('NFL games rendered but no streaming availability rows appeared')

    rows = []
    for key in sorted(REQUIRED):
        a = v4['data'].get(key, {'count':0,'titles':[],'duplicateTitles':0})
        b = v5['data'].get(key, {'count':0,'titles':[],'duplicateTitles':0})
        aset = {norm(x) for x in a['titles'] if norm(x)}
        bset = {norm(x) for x in b['titles'] if norm(x)}
        union = aset | bset
        rows.append({
            'tab': key,
            'v4Count': a['count'],
            'v5Count': b['count'],
            'v4Duplicates': a['duplicateTitles'],
            'v5Duplicates': b['duplicateTitles'],
            'overlap': len(aset & bset),
            'jaccard': round(len(aset & bset) / len(union), 3) if union else 1.0,
        })

    report = {
        'status':'fail' if failures else 'pass',
        'location':'Farmington, NM',
        'v4Errors':v4['errors'],
        'v5Errors':v5['errors'],
        'v4Tabs':v4['tabs'],
        'v5Tabs':v5['tabs'],
        'v5Extra':v5['extra'],
        'tabComparison':rows,
        'failures':failures,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('FINAL V4 ↔ V5 TAB AUDIT')
    print('TAB             V4  V5  V4DUP V5DUP OVERLAP JACCARD')
    for row in rows:
        print(f"{row['tab'][:15]:15} {row['v4Count']:3} {row['v5Count']:3} {row['v4Duplicates']:5} {row['v5Duplicates']:5} {row['overlap']:7} {row['jaccard']:7.3f}")
    if failures:
        for failure in failures:
            print('FAIL', failure)
        raise SystemExit(f'V5 final browser audit failed with {len(failures)} issue(s).')
    print('V5 FINAL BROWSER AUDIT PASS')


if __name__ == '__main__':
    main()
