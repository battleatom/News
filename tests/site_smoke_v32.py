from __future__ import annotations

from playwright.sync_api import sync_playwright
import site_smoke_v26 as base

BASE=base.BASE
EXPECTED_X=['Health','Technology & AI','Celebrities & Public Figures','World','Politics & Government','Entertainment','Sports','Business & Economy','Gaming','Science']


def farmington_suite(browser):
    context=browser.new_context(viewport={'width':1440,'height':950},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');page.wait_for_timeout(1800)
    assert page.evaluate('window.__locationContentV26===true'), 'Merged State controller missing'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0, 'Local remains a separate tab'
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0, 'Region remains a separate tab'
    assert page.locator('#tabs > .tab[data-nav-key="nm"]').count()==1, 'State tab missing'
    assert 'New Mexico' in page.locator('#tabs > .tab[data-nav-key="nm"]').inner_text(), 'Farmington did not resolve to New Mexico State tab'

    base.click_key(page,'presidential')
    assert page.locator('#news-feed .news-item').count()>0, 'Presidential section is empty'
    assert page.evaluate('paginatedNewsItems(allItems).available.every(i=>window.__presidentialRelevantV26(i))'), 'Foreign/non-presidential story survived Presidential filter'

    base.click_key(page,'nm')
    counts=page.evaluate('window.__stateMergeCountsV26')
    # Live supply naturally varies. Exact 6/6/6 behavior is enforced below by the
    # deterministic synthetic Denver test; here require genuine state/regional depth.
    assert counts and counts['state']>0 and counts['regional']>0 and 0<=counts['local']<=6, f'Farmington State mix is invalid: {counts}'
    local_texts=page.evaluate("""() => window.__mergedStatePoolV26(allItems)
      .filter(i=>(i.querySelector('locationTier')?.textContent||'')==='Local')
      .map(i=>`${i.querySelector('title')?.textContent||''} ${i.querySelector('description')?.textContent||''}`.toLowerCase())""")
    local_terms=('farmington','san juan county','aztec','bloomfield','kirtland','shiprock','four corners')
    assert all(any(term in text for term in local_terms) for text in local_texts), f'Non-local story was labeled Local: {local_texts}'
    base.infinite_scroll_check(page)
    base.badge_checks(page)
    base.content_brief_checks(page)
    assert not errors, f'Browser errors: {errors[:5]}'
    context.close()


def mobile_suite(browser):
    context=browser.new_context(viewport={'width':390,'height':844},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');page.wait_for_timeout(1400)
    assert page.locator('#tabs > .tab').count()>=15, 'Merged mobile navigation lost categories'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0

    base.click_key(page,'x')
    cards=page.locator('#news-feed .x-issue-item')
    assert cards.count()==10, f'X UI rendered {cards.count()} cards instead of 10'
    topics=page.locator('#news-feed .x-topic').all_inner_texts()
    assert [t.upper() for t in topics]==[t.upper() for t in EXPECTED_X], f'X UI topic order/content mismatch: {topics}'
    assert len({t.upper() for t in topics})==10, f'X UI contains duplicate topic labels: {topics}'

    page.evaluate('window.scrollTo(0, Math.min(1400, document.documentElement.scrollHeight-600))')
    page.wait_for_timeout(250)
    positions=page.evaluate("""() => ({
      toolbar:document.querySelector('.toolbar')?.getBoundingClientRect().top,
      tabs:document.querySelector('.tabs')?.getBoundingClientRect().top,
      scrollY:window.scrollY
    })""")
    assert positions['scrollY']>100, f'Mobile page did not scroll enough for sticky test: {positions}'
    assert abs(positions['toolbar'])<=2, f'Mobile toolbar is not sticky at viewport top: {positions}'
    assert 31<=positions['tabs']<=38, f'Mobile category rail is not sticky below toolbar: {positions}'

    overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
    assert overflow<=4, f'Mobile page overflows horizontally by {overflow}px'
    base.badge_checks(page)
    base.content_brief_checks(page)
    assert not errors, f'Mobile browser errors: {errors[:5]}'
    context.close()


def main():
    base.collector_checks()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        farmington_suite(browser)
        base.denver_suite(browser)
        mobile_suite(browser)
        browser.close()
    print('V3.2 SMOKE PASS — feed logic, X ten-card renderer, location, sticky mobile navigation, briefs, badges and scrolling.')


if __name__=='__main__':
    main()
