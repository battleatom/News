from __future__ import annotations

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import re

BASE='http://127.0.0.1:8765/'


def card_titles(page):
    return [re.sub(r'^\d+\.\s*','',t).strip() for t in page.locator('#news-feed .news-item h3').all_text_contents()]


def click_tab(page, needle):
    needle_l=needle.lower()
    direct=page.locator('#tabs > .tab')
    for i in range(direct.count()):
        tab=direct.nth(i)
        text=(tab.inner_text() or '').strip()
        if needle_l in text.lower() and tab.is_visible():
            tab.click()
            return text
    raise AssertionError(f'Tab not found: {needle}; available={direct.all_text_contents()}')


def click_key(page, key):
    tab=page.locator(f'#tabs > .tab[data-nav-key="{key}"]')
    if not tab.count() or not tab.first.is_visible():
        raise AssertionError(f'Tab key not found: {key}; available={page.locator("#tabs > .tab").all_text_contents()}')
    text=(tab.first.inner_text() or '').strip()
    tab.first.click()
    return text


def wait_feed(page, allow_loading=False):
    page.wait_for_selector('#news-feed')
    if not allow_loading:
        try:
            page.wait_for_function("!document.querySelector('#news-feed')?.innerText?.includes('Loading news')", timeout=12000)
        except PlaywrightTimeoutError:
            raise AssertionError('Feed remained stuck on Loading news')
    text=(page.locator('#news-feed').inner_text() or '').strip()
    assert text, 'Feed rendered no text'
    assert 'Update failed' not in text, f'Feed showed update failure: {text[:200]}'


def assert_unique_visible_titles(page):
    titles=[t.lower() for t in card_titles(page) if t]
    duplicates={t for t in titles if titles.count(t)>1}
    assert not duplicates, f'Exact visible title duplicates: {sorted(duplicates)[:5]}'


def assert_v22_status_and_alerts(page):
    panel=page.locator('#pull-stats-ui')
    assert panel.count()==1 and panel.is_visible(), 'Detailed update status panel missing'
    status_text=panel.inner_text().lower()
    assert 'auto refresh' in status_text, 'Auto-refresh state is missing from status panel'
    assert 'next in' in status_text, 'Live refresh countdown is missing'
    assert 'fetched' in status_text and 'new' in status_text, 'Fetch/new counts are missing'
    assert 'duplicates removed' in status_text, 'Duplicate-removal count is missing'
    assert 'shown' in status_text, 'Final shown count is missing'
    sound=page.locator('#sound-alerts-toggle')
    assert sound.count()==1 and sound.is_visible(), 'Sound-alert enable control is missing'


def desktop_suite(browser):
    context=browser.new_context(
        viewport={'width':1440,'height':1000},
        geolocation={'latitude':36.7281,'longitude':-108.2187},
        permissions=['geolocation'],
    )
    page=context.new_page()
    page_errors=[]
    page.on('pageerror', lambda exc: page_errors.append(str(exc)))
    page.goto(BASE, wait_until='domcontentloaded', timeout=30000)
    wait_feed(page)
    page.wait_for_timeout(1200)

    assert page.evaluate("window.__underreportedV2===true"), 'Underreported 2.0 controller did not start'
    assert page.evaluate("window.__alertsStatusV22===true"), 'Underreported V2.2 status/alert controller did not start'
    assert page.locator('body[data-underreported-version="2"]').count()==1, 'V2 page marker missing'
    assert page.locator('.skip-link-v2').count()==1, 'Accessible skip link missing'
    assert page.locator('#tabs').count()==1, 'Tab bar missing'
    assert page.locator('#more-tab-v2').count()==0, 'Retired More navigation is still present'
    assert page.locator('#more-menu-v2').count()==0, 'Retired More menu is still present'
    assert page.locator('#markets').count()==1 or page.locator('.markets').count()>=1, 'Markets strip missing'

    expected=['Top','NFL','Top Issues','Underreported','World','United States','Presidential','Federal Government','Federal + New Mexico','New Mexico','Local / Four Corners','Southwest','Technology','Gaming','Military','Box Office','Bookmarks']
    direct_labels=[(t or '').strip() for t in page.locator('#tabs > .tab').all_text_contents()]
    for name in expected:
        assert any(name.lower() in label.lower() for label in direct_labels), f'{name} missing from visible tab strip'

    market=page.locator('#markets') if page.locator('#markets').count() else page.locator('.markets').first
    market_overflow=page.evaluate("el=>el.scrollWidth-el.clientWidth", market.element_handle())
    assert market_overflow <= 4, f'Desktop markets overflow horizontally by {market_overflow}px'

    results={}
    for name in expected:
        click_tab(page,name)
        page.wait_for_timeout(350)
        wait_feed(page, allow_loading=name in ('NFL','Box Office'))
        if name in ('NFL','Box Office'):
            page.wait_for_timeout(1800)
        body=(page.locator('#news-feed').inner_text() or '')
        assert body.strip(), f'{name} tab empty/renderless'
        assert 'Loading news' not in body, f'{name} stuck on generic loading state'
        if name not in ('Bookmarks','Box Office','NFL'):
            assert_unique_visible_titles(page)
        results[name]=len(card_titles(page))

    click_tab(page,'Top')
    page.wait_for_timeout(350)
    assert page.locator('#news-feed .news-item').count()>=1, 'Top Stories rendered no cards'
    assert page.locator('#news-feed .lead-story-v2').count()==0, 'Oversized lead-card treatment is still present'
    assert page.locator('#news-feed .news-item-v2-kicker').count()==0, 'Lead-story kicker is still present'
    before=card_titles(page)
    btn=page.locator('#refresh')
    assert btn.is_visible(), 'Next Top Stories button is not visible on Top'
    btn.click()
    page.wait_for_timeout(800)
    after=card_titles(page)
    if len(before)>=10:
        assert before!=after, 'Next Top Stories did not rotate the visible Top batch'

    load_more_verified=False
    for candidate in ('World','United States','Technology','Local / Four Corners','Federal Government'):
        click_tab(page,candidate); page.wait_for_timeout(300)
        more=page.locator('.load-more')
        if more.count() and more.first.is_visible():
            before_count=len(card_titles(page))
            more.first.click(); page.wait_for_timeout(400)
            after_count=len(card_titles(page))
            assert after_count>before_count, f'Load More did not add cards in {candidate}'
            load_more_verified=True
            break
    assert load_more_verified, 'No ordinary category exposed a testable Load More button'

    click_tab(page,'Top'); page.wait_for_timeout(350)
    page.wait_for_selector('.bookmark-btn', timeout=5000)
    first_bookmark=page.locator('.bookmark-btn').first
    first_bookmark.click(); page.wait_for_timeout(200)
    click_tab(page,'Bookmarks'); page.wait_for_timeout(350)
    assert page.locator('#news-feed .news-item').count()>=1, 'Bookmark was not saved/rendered'
    page.locator('#news-feed .bookmark-btn').first.click(); page.wait_for_timeout(250)
    assert 'No saved articles yet' in page.locator('#news-feed').inner_text(), 'Bookmark removal did not persist'

    assert page.evaluate("window.__autoRefreshTimerV1===true"), 'Automatic refresh scheduler did not start'
    assert page.evaluate("Number(window.nextScheduledPull)>Date.now()"), 'Next automatic refresh time is not scheduled'
    assert page.evaluate("Boolean(window.__autoRefreshTimeout)"), 'Timeout-based automatic refresh was not scheduled'
    assert page.locator('#pull-status').count()==0 or not page.locator('#pull-status').is_visible(), 'Duplicate legacy update row is visible'
    assert_v22_status_and_alerts(page)

    # Return to a populated story view before testing badge decoration.
    click_tab(page,'Top'); page.wait_for_timeout(350)
    # Force one visible card to a fresh timestamp and verify the red NEW marker.
    page.evaluate("""() => {
      const card=document.querySelector('#news-feed .news-item');
      const meta=card?.querySelector('.meta span');
      if(meta)meta.textContent=new Date().toISOString();
      window.decorateNewBadges();
    }""")
    assert page.locator('#news-feed .new-badge').count()>=1, 'Fresh article did not receive a red NEW badge'

    sound=page.locator('#sound-alerts-toggle')
    sound.click();page.wait_for_timeout(200)
    assert page.evaluate("localStorage.getItem('underreported-sound-alerts-v2')==='on'"), 'Sound alert preference was not enabled by user gesture'
    assert 'alerts on' in sound.inner_text().lower(), 'Sound control did not confirm alerts are enabled'
    assert page.evaluate("typeof window.playNewArticlePop==='function'"), 'New-article pop function is missing'
    page.evaluate("window.playNewArticlePop()")

    page.evaluate("localStorage.setItem('underreported-state','TX'); localStorage.setItem('underreported-location','Austin, TX');")
    click_key(page,'legislation')
    page.wait_for_timeout(700)
    leg_text=page.locator('#news-feed').inner_text()
    assert 'Congress.gov' in leg_text or 'Federal' in leg_text, 'Federal legislation records missing'
    assert 'New Mexico Legislature' not in leg_text, 'NM legislation leaked into a Texas location view'

    page.evaluate("localStorage.setItem('underreported-state','NM'); localStorage.setItem('underreported-location','Farmington, NM');")
    page.wait_for_timeout(2100)
    click_key(page,'legislation')
    page.wait_for_timeout(500)
    nm_leg=page.locator('#news-feed').inner_text()
    assert 'New Mexico' in nm_leg, 'NM location did not select New Mexico legislation view'

    assert not page_errors, 'Uncaught page errors: '+json.dumps(page_errors[:5])
    context.close()
    return results


def mobile_suite(browser):
    context=browser.new_context(viewport={'width':390,'height':844})
    page=context.new_page()
    page.goto(BASE, wait_until='domcontentloaded', timeout=30000)
    wait_feed(page)
    page.wait_for_timeout(800)
    body_overflow=page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
    assert body_overflow <= 4, f'Mobile page body overflows horizontally by {body_overflow}px'
    assert page.locator('#more-tab-v2').count()==0, 'Mobile More navigation still exists'
    assert page.locator('#tabs > .tab').count()>=17, 'Mobile tab strip is missing categories'
    tab_overflow=page.evaluate("el=>el.scrollWidth-el.clientWidth", page.locator('#tabs').element_handle())
    assert tab_overflow>20, 'Mobile category strip should scroll horizontally instead of hiding tabs'
    click_tab(page,'Top')
    page.wait_for_timeout(250)
    assert page.locator('#news-feed .lead-story-v2').count()==0, 'Mobile oversized lead card still exists'
    first=page.locator('#news-feed .news-item').first
    assert first.count()==1, 'Mobile Top Stories rendered no first card'
    pad_top=float(page.evaluate("el=>parseFloat(getComputedStyle(el).paddingTop)", first.element_handle()))
    pad_left=float(page.evaluate("el=>parseFloat(getComputedStyle(el).paddingLeft)", first.element_handle()))
    assert pad_top<=12 and pad_left<=11, f'Mobile card padding is too large: top={pad_top}, left={pad_left}'
    assert page.locator('#pull-status').count()==0 or not page.locator('#pull-status').is_visible(), 'Mobile duplicate update row is visible'
    assert_v22_status_and_alerts(page)
    context.close()


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        results=desktop_suite(browser)
        mobile_suite(browser)
        browser.close()
    print('BROWSER SMOKE PASS')
    for key,value in results.items():
        print(f'  {key:24} visible cards: {value}')


if __name__=='__main__':
    main()
