from __future__ import annotations

import runpy
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'


def click_key(page,key):
    tab=page.locator(f'#tabs > .tab[data-nav-key="{key}"]')
    assert tab.count()==1 and tab.is_visible(), f'Missing visible tab {key}'
    tab.click();page.wait_for_timeout(350)


def collector_checks():
    ns=runpy.run_path('scripts/update_news.py')
    check=ns.get('is_us_presidential_story')
    assert callable(check), 'Strict Presidential collector helper is missing'
    assert check('President Trump signs new executive order at White House','United States policy update')
    assert check('Trump meets foreign leaders at White House','U.S. president hosts talks')
    assert not check('Brazil president announces new economic plan','Government in Brasilia releases details')
    assert not check('French president addresses parliament','Paris government update')
    assert not check('President signs sweeping reform bill','Foreign parliament approved the measure')
    region_selector=ns.get('select_region_stories')
    assert callable(region_selector), 'Per-state regional depth selector is missing'


def badge_checks(page):
    assert page.evaluate('window.__alertsNewV26===true'), 'V2.6 NEW badge controller missing'
    now=page.evaluate('Date.now()')
    def state(pub_age_h,site_age_h):
        return page.evaluate('([p,f,n])=>window.__classifyNewBadgeV26(p,f,n)',[now-pub_age_h*3600000,now-site_age_h*3600000,now])
    assert state(10,.5)=='red', 'First hour on site must be red NEW'
    assert state(2,2)=='blue', 'Publication within three hours must be blue NEW after red expires'
    assert state(10,2)=='yellow', 'Older article newly added within three hours must be yellow NEW'
    assert state(4,2)=='', 'Article aged 3-6 hours should have no secondary NEW badge'
    assert state(10,4)=='', 'Yellow NEW must expire three hours after first seen'


def synthetic_denver_mix(page):
    return page.evaluate("""() => {
      const rows=[];
      const now=new Date().toUTCString();
      function add(title,link,state,region){
        const xml=`<item><title>${title}</title><link>${link}</link><description>${title}</description><pubDate>${now}</pubDate><source>Test Source</source><category>region</category><region>${region}</region><state>${state}</state></item>`;
        rows.push(new DOMParser().parseFromString(xml,'text/xml').documentElement);
      }
      for(let i=1;i<=6;i++)add(`Denver local test ${i}`,`https://example.com/denver-${i}`,'Colorado','mountain');
      for(let i=1;i<=6;i++)add(`Colorado statewide test ${i}`,`https://example.com/colorado-${i}`,'Colorado','mountain');
      for(let i=1;i<=6;i++)add(`Wyoming mountain regional test ${i}`,`https://example.com/mountain-${i}`,'Wyoming','mountain');
      const result=window.__mergedStatePoolV26(rows);
      return {
        counts:window.__stateMergeCountsV26,
        tiers:result.slice(0,18).map(i=>i.querySelector('locationTier')?.textContent||''),
        links:result.slice(0,18).map(i=>i.querySelector('link')?.textContent||'')
      };
    }""")


def farmington_suite(browser):
    context=browser.new_context(viewport={'width':1440,'height':950},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');page.wait_for_timeout(1800)
    assert page.evaluate('window.__locationContentV26===true'), 'Merged State controller missing'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0, 'Local remains a separate tab'
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0, 'Region remains a separate tab'
    assert page.locator('#tabs > .tab[data-nav-key="nm"]').count()==1, 'State tab missing'
    assert 'New Mexico' in page.locator('#tabs > .tab[data-nav-key="nm"]').inner_text(), 'Farmington did not resolve to New Mexico State tab'

    click_key(page,'presidential')
    assert page.locator('#news-feed .news-item').count()>0, 'Presidential section is empty'
    assert page.evaluate('paginatedNewsItems(allItems).available.every(i=>window.__presidentialRelevantV26(i))'), 'Foreign/non-presidential story survived Presidential filter'

    click_key(page,'nm')
    counts=page.evaluate('window.__stateMergeCountsV26')
    assert counts and counts['state']>=6 and counts['regional']>=6 and counts['local']>=6, f'Farmington State lead mix does not have at least 6/6/6 candidates: {counts}'
    more=page.locator('.load-more');assert more.count() and more.is_visible(), 'Merged State feed has no Load More'
    before=page.locator('#news-feed .news-item').count();more.click();page.wait_for_timeout(350);after=page.locator('#news-feed .news-item').count()
    assert after>before, 'Merged State Load More did not add stories'
    badge_checks(page)
    assert not errors, f'Browser errors: {errors[:5]}'
    context.close()


def denver_suite(browser):
    context=browser.new_context(viewport={'width':1440,'height':950},geolocation={'latitude':39.7392,'longitude':-104.9903},permissions=['geolocation'])
    page=context.new_page();page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');page.wait_for_timeout(1800)
    label=page.locator('#tabs > .tab[data-nav-key="nm"]').inner_text()
    assert 'Colorado' in label, f'Denver did not resolve to Colorado State tab: {label}'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0
    click_key(page,'nm')
    live_counts=page.evaluate('window.__stateMergeCountsV26')
    assert live_counts and live_counts['location']['code']=='CO', f'Denver State pool used wrong location: {live_counts}'

    synthetic=synthetic_denver_mix(page)
    counts=synthetic['counts']
    assert counts['state']==6 and counts['regional']==6 and counts['local']==6, f'Deterministic Denver State mix is not 6/6/6: {synthetic}'
    assert synthetic['tiers'][:6]==['State']*6, f'First six merged stories are not State: {synthetic["tiers"]}'
    assert synthetic['tiers'][6:12]==['Regional']*6, f'Second six merged stories are not Regional: {synthetic["tiers"]}'
    assert synthetic['tiers'][12:18]==['Local']*6, f'Third six merged stories are not Local: {synthetic["tiers"]}'
    assert len(set(synthetic['links']))==18, 'Merged 6/6/6 lead mix duplicated an article'
    context.close()


def mobile_suite(browser):
    context=browser.new_context(viewport={'width':390,'height':844},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');page.wait_for_timeout(1200)
    assert page.locator('#tabs > .tab').count()>=15, 'Merged mobile navigation lost categories'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0
    overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
    assert overflow<=4, f'Mobile page overflows horizontally by {overflow}px'
    badge_checks(page);context.close()


def main():
    collector_checks()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        farmington_suite(browser);denver_suite(browser);mobile_suite(browser)
        browser.close()
    print('V2.6 SMOKE PASS — Presidential strict, merged State 6/6/6 logic, location switching, tiered NEW badges.')


if __name__=='__main__':
    main()
