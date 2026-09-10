from __future__ import annotations

import json
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE='http://127.0.0.1:8765/'
EXPECTED_KEYS=['top','nfl','x','underreported','world','us','presidential','federal','legislation','nm','technology','gaming','military','boxoffice','bookmarks']


def wait_feed(page, allow_loading=False):
    page.wait_for_selector('#news-feed')
    if not allow_loading:
        try:
            page.wait_for_function("!document.querySelector('#news-feed')?.innerText?.includes('Loading news')", timeout=12000)
        except PlaywrightTimeoutError:
            raise AssertionError('Feed remained stuck on Loading news')
    text=(page.locator('#news-feed').inner_text() or '').strip()
    assert text, 'Feed rendered no text'
    assert 'Update failed' not in text, f'Feed showed update failure: {text[:180]}'


def click_key(page,key):
    tab=page.locator(f'#tabs > .tab[data-nav-key="{key}"]')
    assert tab.count()==1 and tab.is_visible(), f'Missing visible tab {key}'
    tab.click();page.wait_for_timeout(300)


def titles(page):
    return [re.sub(r'^\d+\.\s*','',x).strip() for x in page.locator('#news-feed .news-item h3').all_text_contents()]


def desktop_suite(browser):
    context=browser.new_context(viewport={'width':1440,'height':950},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);wait_feed(page);page.wait_for_timeout(1600)

    assert page.evaluate('window.__underreportedV2===true')
    assert page.evaluate('window.__underreportedV28Optimized===true'), 'V2.8 optimized runtime did not start'
    assert page.evaluate('window.__alertsStatusV22===true'), 'Status controller missing'
    assert page.evaluate('window.__alertsNewV23===true'), 'NEW/audio controller missing'
    assert page.evaluate('window.__alertsNewV26===true'), 'V2.6 NEW classifier missing'
    assert page.evaluate('window.__locationContentV26===true'), 'Location content controller missing'
    assert page.evaluate('window.__autoRefreshTimerV1===true'), 'Auto-refresh timer missing'

    tabs=page.locator('#tabs > .tab')
    keys=tabs.evaluate_all("els=>els.map(x=>x.dataset.navKey).filter(Boolean)")
    for key in EXPECTED_KEYS:
        assert key in keys, f'Missing tab key {key}; got {keys}'
    assert 'local' not in keys and 'region' not in keys, 'Retired standalone Local/Region tabs returned'
    assert page.locator('#tabs > .tab[data-nav-key="nm"]').count()==1
    assert 'New Mexico' in page.locator('#tabs > .tab[data-nav-key="nm"]').inner_text(), 'Detected State tab not labeled New Mexico'

    assert page.locator('#markets').count()==1 or page.locator('.markets').count()>=1, 'Markets strip missing'
    sound=page.locator('#sound-alerts-toggle');assert sound.count()==1 and sound.is_visible(), 'Sound toggle missing'
    before_enabled=sound.get_attribute('data-enabled')
    sound.click();page.wait_for_timeout(250)
    after_enabled=sound.get_attribute('data-enabled')
    assert after_enabled is not None, 'Sound toggle did not expose enabled state'
    assert before_enabled!=after_enabled or after_enabled=='true', 'Sound toggle did not react to click'

    panel=page.locator('#pull-stats-ui');assert panel.count()==1 and panel.is_visible(), 'Live status panel missing'
    panel_text=panel.inner_text().lower()
    assert 'live' in panel_text or 'refresh' in panel_text, 'Live status panel has no live/update state'

    # Exercise every current navigation target. Bookmarks may legitimately be empty.
    for key in EXPECTED_KEYS:
        click_key(page,key)
        if key in ('nfl','boxoffice'):
            page.wait_for_timeout(1400)
        wait_feed(page,allow_loading=key in ('nfl','boxoffice'))
        body=(page.locator('#news-feed').inner_text() or '').strip()
        assert 'Loading news' not in body, f'{key} stayed in loading state'
        if key!='bookmarks':
            assert body, f'{key} rendered empty content'
        visible=[t.lower() for t in titles(page) if t]
        assert len(visible)==len(set(visible)), f'Exact duplicate visible titles in {key}'

    # Top Stories discovery/refresh control.
    click_key(page,'top');page.wait_for_timeout(300)
    refresh=page.locator('#refresh');assert refresh.is_visible(), 'Next Top Stories button hidden on Top'
    before=titles(page)
    refresh.click();page.wait_for_timeout(900)
    after=titles(page)
    assert not refresh.is_disabled(), 'Top Stories button stayed disabled after click'
    if len(before)>=10: assert before!=after, 'Top Stories button did not rotate visible stories'

    # NEW badge/tag path.
    first=page.locator('#news-feed .news-item').first
    href=first.locator('h3 a').get_attribute('href');assert href
    page.evaluate('href=>window.__markNewArticleLinksV23([href])',href)
    assert first.locator('.new-badge').count()==1, 'NEW tag did not render on marked story'

    # Bookmark save/remove and Bookmarks tab.
    page.wait_for_selector('.bookmark-btn',timeout=5000)
    page.locator('.bookmark-btn').first.click();page.wait_for_timeout(200)
    click_key(page,'bookmarks');page.wait_for_timeout(250)
    assert page.locator('#news-feed .news-item').count()>=1, 'Saved bookmark did not render'
    page.locator('#news-feed .bookmark-btn').first.click();page.wait_for_timeout(250)
    assert 'No saved articles yet' in page.locator('#news-feed').inner_text(), 'Bookmark removal failed'

    # Merged detected-state content must expose State/Regional tiers and only true Local matches.
    click_key(page,'nm');page.wait_for_timeout(350)
    counts=page.evaluate('window.__stateMergeCountsV26')
    assert counts and counts['state']>=1 and counts['regional']>=1, f'Merged State content invalid: {counts}'
    local_texts=page.evaluate("""() => window.__mergedStatePoolV26(allItems)
      .filter(i=>(i.querySelector('locationTier')?.textContent||'')==='Local')
      .map(i=>`${i.querySelector('title')?.textContent||''} ${i.querySelector('description')?.textContent||''}`.toLowerCase())""")
    local_terms=('farmington','san juan county','aztec','bloomfield','kirtland','shiprock','four corners')
    assert all(any(term in text for term in local_terms) for text in local_texts), f'False Local tag found: {local_texts}'

    # Legislation, related coverage, NFL and box-office controllers must be installed/live.
    click_key(page,'legislation');page.wait_for_timeout(400)
    assert page.locator('#news-feed').inner_text().strip(), 'Legislation view empty'
    assert page.evaluate("typeof window.__presidentialRelevantV26==='function'"), 'Presidential relevance filter missing'
    click_key(page,'nfl');page.wait_for_timeout(1200)
    assert page.locator('#news-feed').inner_text().strip(), 'NFL view empty'
    click_key(page,'boxoffice');page.wait_for_timeout(1200)
    assert page.locator('#news-feed').inner_text().strip(), 'Box Office view empty'

    assert page.evaluate('Number(window.nextScheduledPull)>Date.now()'), 'No future auto-refresh scheduled'
    assert page.evaluate('Boolean(window.__autoRefreshTimeout)'), 'Auto-refresh timeout missing'
    assert page.locator('#pull-status').count()==0 or not page.locator('#pull-status').is_visible(), 'Duplicate legacy status row visible'
    assert not errors, 'Uncaught browser errors: '+json.dumps(errors[:8])
    context.close()


def mobile_suite(browser):
    context=browser.new_context(viewport={'width':390,'height':844},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);wait_feed(page);page.wait_for_timeout(1000)
    overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
    assert overflow<=4, f'Mobile page overflows horizontally by {overflow}px'
    keys=page.locator('#tabs > .tab').evaluate_all("els=>els.map(x=>x.dataset.navKey).filter(Boolean)")
    for key in EXPECTED_KEYS: assert key in keys, f'Mobile missing {key}'
    assert page.locator('#sound-alerts-toggle').is_visible(), 'Mobile sound toggle missing'
    assert page.locator('#pull-stats-ui').is_visible(), 'Mobile live status missing'
    click_key(page,'top');assert page.locator('#refresh').is_visible(), 'Mobile Top button missing'
    assert not errors, 'Mobile browser errors: '+json.dumps(errors[:8])
    context.close()


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        desktop_suite(browser);mobile_suite(browser)
        browser.close()
    print('V2.8 FULL FEATURE SMOKE PASS — navigation, feeds, buttons, sound toggle, NEW tags, bookmarks, location/state, legislation, NFL, box office, markets and mobile.')


if __name__=='__main__':
    main()
