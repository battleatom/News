from __future__ import annotations

from playwright.sync_api import sync_playwright
import site_smoke_v26 as base

BASE=base.BASE
EXPECTED_X=['Health','Technology & AI','Celebrities & Public Figures','World','Politics & Government','Entertainment','Sports','Business & Economy','Gaming','Science']


def wait_for_location_v36(page):
    page.wait_for_function('window.__locationContentV36===true',timeout=10000)
    page.wait_for_function('window.__locationCityOnlyV1===true',timeout=10000)
    page.wait_for_timeout(900)


def location_scope_labels(page):
    page.wait_for_selector('.location-scope-bar',timeout=10000)
    return page.locator('.location-scope-bar .location-scope-btn').all_inner_texts()


def farmington_suite(browser):
    context=browser.new_context(viewport={'width':1440,'height':950},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');wait_for_location_v36(page)
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0, 'Local remains a separate tab'
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0, 'Region remains a separate tab'
    assert page.locator('#tabs > .tab[data-nav-key="nm"]').count()==1, 'State tab missing'
    assert 'New Mexico' in page.locator('#tabs > .tab[data-nav-key="nm"]').inner_text(), 'Farmington did not resolve to New Mexico State tab'

    base.click_key(page,'presidential')
    assert page.locator('#news-feed .news-item').count()>0, 'Presidential section is empty'
    assert page.evaluate("paginatedNewsItems(allItems).available.every(i=>(i.querySelector('category')?.textContent||'').trim().toLowerCase()==='presidential')"), 'Non-presidential story survived Presidential category routing'
    assert page.evaluate("window.__presidentialRelevantV26===undefined"), 'Legacy browser Presidential classifier unexpectedly active'

    base.click_key(page,'nm')
    labels=location_scope_labels(page)
    joined=' | '.join(labels)
    assert 'All' in joined and 'Statewide' in joined, f'Missing state hub scopes: {joined}'
    assert 'Farmington' in joined or 'Local' in joined, f'Missing city scope: {joined}'
    assert 'Southwest' in joined or 'Region' in joined, f'Missing regional scope: {joined}'
    assert 'County' not in joined and 'San Juan County' not in joined, f'County scope should be hidden: {joined}'
    assert page.locator('.location-scope-btn[data-scope="county"]').count()==0, 'County scope button is still visible'

    pools=page.evaluate("""() => ({
      local:window.__locationLocalPoolV36(allItems).length,
      state:window.__locationStatePoolV36(allItems).length,
      region:window.__locationRegionPoolV36(allItems).length,
      merged:window.__mergedLocationPoolV36(allItems).length,
      counts:window.__locationHubCountsV36
    })""")
    assert pools['local']>0 and pools['state']>0 and pools['region']>0 and pools['merged']>0, f'Farmington V36 location pools are invalid: {pools}'
    assert pools['counts'] and pools['counts']['location']['code']=='NM', f'Farmington V36 location context is invalid: {pools}'

    base.infinite_scroll_check(page)
    base.badge_checks(page)
    base.content_brief_checks(page)
    assert not errors, f'Browser errors: {errors[:5]}'
    context.close()


def denver_suite(browser):
    context=browser.new_context(viewport={'width':1440,'height':950},geolocation={'latitude':39.7392,'longitude':-104.9903},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');wait_for_location_v36(page)
    label=page.locator('#tabs > .tab[data-nav-key="nm"]').inner_text()
    assert 'Colorado' in label, f'Denver did not resolve to Colorado State tab: {label}'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0

    base.click_key(page,'nm')
    labels=location_scope_labels(page)
    joined=' | '.join(labels)
    assert 'Statewide' in joined and ('Denver' in joined or 'Local' in joined), f'Denver location scopes invalid: {joined}'
    assert 'County' not in joined, f'County scope should be hidden in Denver: {joined}'
    assert page.locator('.location-scope-btn[data-scope="county"]').count()==0

    pools=page.evaluate("""() => ({
      local:window.__locationLocalPoolV36(allItems).length,
      state:window.__locationStatePoolV36(allItems).length,
      region:window.__locationRegionPoolV36(allItems).length,
      merged:window.__mergedLocationPoolV36(allItems).length,
      counts:window.__locationHubCountsV36
    })""")
    assert pools['counts'] and pools['counts']['location']['code']=='CO', f'Denver V36 location context is invalid: {pools}'
    assert pools['state']>0 and pools['region']>0 and pools['merged']>0, f'Denver V36 location pools are invalid: {pools}'
    assert not errors, f'Denver browser errors: {errors[:5]}'
    context.close()


def mobile_suite(browser):
    context=browser.new_context(viewport={'width':390,'height':844},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');wait_for_location_v36(page)
    assert page.locator('#tabs > .tab').count()>=15, 'Merged mobile navigation lost categories'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0

    base.click_key(page,'nm')
    assert page.locator('.location-scope-btn[data-scope="county"]').count()==0, 'County scope button is visible on mobile'

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

    base.click_key(page,'top')
    base.badge_checks(page)
    base.content_brief_checks(page)
    assert not errors, f'Mobile browser errors: {errors[:5]}'
    context.close()


def main():
    base.collector_checks()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        farmington_suite(browser)
        denver_suite(browser)
        mobile_suite(browser)
        browser.close()
    print('V4 SMOKE PASS — feed logic, Presidential routing, X renderer, city-only V36 location hub, sticky mobile navigation, briefs, badges and scrolling.')


if __name__=='__main__':
    main()
