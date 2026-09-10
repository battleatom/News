from __future__ import annotations

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import re

BASE='http://127.0.0.1:8765/'


def card_titles(page):
    return [re.sub(r'^\d+\.\s*','',t).strip() for t in page.locator('#news-feed .news-item h3').all_text_contents()]


def click_key(page,key):
    tab=page.locator(f'#tabs > .tab[data-nav-key="{key}"]')
    if not tab.count() or not tab.first.is_visible():
        raise AssertionError(f'Tab key not found: {key}; available={page.locator("#tabs > .tab").all_text_contents()}')
    tab.first.click(); page.wait_for_timeout(300)


def wait_feed(page,allow_loading=False,label='unknown'):
    page.wait_for_selector('#news-feed')
    if not allow_loading:
        try: page.wait_for_function("!document.querySelector('#news-feed')?.innerText?.includes('Loading news')",timeout=12000)
        except PlaywrightTimeoutError: raise AssertionError(f'{label}: feed remained stuck on Loading news')
    text=(page.locator('#news-feed').inner_text() or '').strip()
    assert text, f'{label}: feed rendered no text'
    assert 'Update failed' not in text, f'{label}: '+text[:200]


def unique_titles(page):
    titles=[t.lower() for t in card_titles(page) if t]
    dupes={t for t in titles if titles.count(t)>1}
    assert not dupes, f'Exact visible title duplicates: {sorted(dupes)[:5]}'


def assert_status(page):
    panel=page.locator('#pull-stats-ui')
    assert panel.count()==1 and panel.is_visible(), 'Update status panel missing'
    txt=panel.inner_text().lower()
    for marker in ('auto refresh','next in','fetched','new','duplicates removed','shown'):
        assert marker in txt, f'Status marker missing: {marker}'
    assert page.locator('#sound-alerts-toggle').count()==1 and page.locator('#sound-alerts-toggle').is_visible()


def set_cached_location(page,city,state,lat,lon,active_tab='legislation'):
    page.evaluate("""([city,state,lat,lon,activeTab])=>{
      const value={city,state,lat,lon,label:`${city}, ${state}`,source:'test',savedAt:Date.now()};
      localStorage.setItem('underreported-location-v2',JSON.stringify(value));
      localStorage.setItem('underreported-state',state);
      localStorage.setItem('underreported-location',value.label);
      localStorage.setItem('underreported-active-tab',activeTab);
    }""",[city,state,lat,lon,active_tab])
    page.reload(wait_until='domcontentloaded')
    wait_feed(page,label=f'{city} reload')
    page.wait_for_timeout(900)
    tab=page.locator(f'#tabs > .tab[data-nav-key="{active_tab}"]')
    assert tab.count()==1 and tab.first.is_visible(), f'{city}: expected tab {active_tab}'
    if page.evaluate('window.active')!=active_tab:
        tab.first.click(); page.wait_for_timeout(350)
    wait_feed(page,label=f'{city} {active_tab}')
    assert page.evaluate('window.active')==active_tab, f'{city}: expected active tab {active_tab}'


def desktop(browser):
    context=browser.new_context(viewport={'width':1440,'height':1000},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page(); errors=[]; page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000); wait_feed(page,label='initial'); page.wait_for_timeout(1300)

    for expr,msg in [
        ('window.__underreportedV2===true','V2 controller missing'),
        ('window.__alertsStatusV22===true','status controller missing'),
        ('window.__alertsNewV281===true','V2.8.1 NEW/audio controller missing'),
        ('window.__autoRefreshTimerV1===true','auto refresh missing'),
        ('window.__locationContentV26===true','location controller missing'),
    ]: assert page.evaluate(expr),msg

    assert page.locator('body[data-underreported-version="2"]').count()==1
    assert page.locator('.skip-link-v2').count()==1
    assert page.locator('#markets').count()==1 or page.locator('.markets').count()>=1
    assert page.locator('#more-tab-v2').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0

    keys=['top','nfl','x','underreported','world','us','presidential','federal','legislation','nm','technology','gaming','military','boxoffice','bookmarks']
    for key in keys:
        print('CHECK TAB',key,flush=True)
        click_key(page,key)
        wait_feed(page,allow_loading=key in ('nfl','boxoffice'),label=key)
        if key in ('nfl','boxoffice'): page.wait_for_timeout(1500)
        body=(page.locator('#news-feed').inner_text() or '').strip()
        assert body and 'Loading news' not in body, f'{key} failed to render'
        if key not in ('bookmarks','boxoffice','nfl'): unique_titles(page)

    click_key(page,'top')
    assert page.locator('#refresh').is_visible(), 'Next Top Stories button missing'
    before=card_titles(page); page.locator('#refresh').click(); page.wait_for_timeout(700); after=card_titles(page)
    if len(before)>=10: assert before!=after, 'Next Top Stories did not rotate visible batch'

    page.wait_for_selector('.bookmark-btn',timeout=5000)
    page.locator('.bookmark-btn').first.click(); page.wait_for_timeout(150)
    click_key(page,'bookmarks')
    assert page.locator('#news-feed .news-item').count()>=1, 'Bookmark did not render'
    page.locator('#news-feed .bookmark-btn').first.click(); page.wait_for_timeout(200)
    assert 'No saved articles yet' in page.locator('#news-feed').inner_text()

    assert page.evaluate('Number(window.nextScheduledPull)>Date.now()')
    assert page.evaluate('Boolean(window.__autoRefreshTimeout)')
    assert_status(page)

    now=page.evaluate('Date.now()')
    def cls(hours,first_hours=0):
        return page.evaluate('([p,f,n])=>window.__classifyNewBadgeV26(p,f,n)',[now-hours*3600000,now-first_hours*3600000 if first_hours else 0,now])
    assert cls(.5,10)=='red'; assert cls(2,0)=='blue'; assert cls(4,.1)=='yellow'; assert cls(7,.1)==''

    set_cached_location(page,'Austin','TX',30.2672,-97.7431)
    tx=page.locator('#news-feed').inner_text()
    assert 'Congress.gov' in tx or 'Federal' in tx, tx[:500]
    assert 'New Mexico Legislature' not in tx

    set_cached_location(page,'Farmington','NM',36.7281,-108.2187)
    nm_text=page.locator('#news-feed').inner_text()
    assert 'New Mexico' in nm_text, nm_text[:500]

    assert not errors, 'Uncaught page errors: '+json.dumps(errors[:5])
    context.close()


def mobile(browser):
    context=browser.new_context(viewport={'width':390,'height':844},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page(); page.goto(BASE,wait_until='domcontentloaded',timeout=30000); wait_feed(page,label='mobile initial'); page.wait_for_timeout(900)
    overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
    assert overflow<=4, f'Mobile body overflow {overflow}px'
    assert page.locator('#tabs > .tab').count()>=15
    assert page.evaluate("el=>el.scrollWidth-el.clientWidth",page.locator('#tabs').element_handle())>20
    click_key(page,'top')
    first=page.locator('#news-feed .news-item').first; assert first.count()==1
    pad_top=float(page.evaluate('el=>parseFloat(getComputedStyle(el).paddingTop)',first.element_handle()))
    pad_left=float(page.evaluate('el=>parseFloat(getComputedStyle(el).paddingLeft)',first.element_handle()))
    assert pad_top<=12 and pad_left<=11
    assert_status(page)
    context.close()


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        desktop(browser); mobile(browser); browser.close()
    print('CURRENT FULL FEATURE BROWSER SMOKE PASS')

if __name__=='__main__': main()
