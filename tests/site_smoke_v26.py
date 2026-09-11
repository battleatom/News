from __future__ import annotations

import runpy
from collections import Counter
from datetime import datetime, timedelta, timezone
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

    same_event=ns.get('same_event_topic')
    top_selector=ns.get('select_top_stories')
    assert callable(same_event) and callable(top_selector), 'Event-first Top selector is missing'

    now=datetime.now(timezone.utc)
    counter=0
    def story(title,source,minutes=10,description=''):
        nonlocal counter
        counter+=1
        published=now-timedelta(minutes=minutes)
        return {
            'title':title,
            'link':f'https://example.com/story-{counter}',
            'description':description or title,
            'pubDate':published.strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'published':published,
            'source':source,
            'category':'top',
        }

    event=[
        story('Iran missile strike hits Gulf military base','Reuters',5),
        story('Gulf military base hit by Iran missile strike','Associated Press',7),
        story('Iran launches missile strike at Gulf military base','BBC',9),
    ]
    assert same_event(event[0],event[1]), 'Clearly equivalent event headlines do not cluster'

    filler_titles=[
        'Supreme Court issues voting rights ruling',
        'Wildfire forces California evacuations',
        'Hospital network reports cybersecurity breach',
        'Federal Reserve changes interest rate policy',
        'Airline cancels flights after nationwide outage',
        'Congress advances defense spending bill',
        'Major retailer files for bankruptcy protection',
        'Food company recalls contaminated product',
        'Tornado damages Oklahoma communities',
        'Technology company launches new processor',
        'Senate holds hearing on housing costs',
        'Earthquake strikes Alaska coast',
        'Automaker announces large worker layoffs',
        'State officials declare drought emergency',
        'Election officials update ballot rules',
    ]
    sources=['Reuters','Associated Press','BBC','CNN','CBS News']
    filler=[story(title,sources[i%len(sources)],15+i) for i,title in enumerate(filler_titles)]
    selected=top_selector(event+filler)
    event_selected=[x for x in selected if 'iran' in x['title'].lower() and 'missile' in x['title'].lower()]
    assert len(event_selected)==1, f'Same event survived as multiple Top cards: {[x["title"] for x in event_selected]}'
    related_sources={x.get('source') for x in event_selected[0].get('_relatedArticles',[])}
    assert len(related_sources)>=2, f'Event cluster did not preserve multi-outlet coverage: {related_sources}'
    assert len(selected)>=10, 'Synthetic Top pool did not retain enough stories for diversity validation'
    visible_sources=Counter(x.get('source') for x in selected[:10])
    assert max(visible_sources.values())<=2, f'First ten Top stories are publisher-heavy: {visible_sources}'


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


def content_brief_checks(page):
    assert page.locator('html[data-content-briefs="1"]').count()==1, 'V3 content brief presentation marker missing'
    stats=page.evaluate("""() => {
      const items=(window.allItems||[]);
      const generated=items.filter(i=>(i.querySelector('briefGenerated')?.textContent||'')==='true');
      const backed=generated.filter(i=>(i.querySelector('briefSource')?.textContent||'')!=='headline-fallback');
      const rendered=[...document.querySelectorAll('#news-feed .news-item .description')].filter(el=>el.textContent.trim().length>=35);
      return {total:items.length,generated:generated.length,backed:backed.length,rendered:rendered.length};
    }""")
    assert stats['generated']>=max(10,int(stats['total']*.8)), f'Too few generated content briefs: {stats}'
    assert stats['backed']>=max(10,int(stats['total']*.05)), f'Article-backed content briefs missing: {stats}'
    assert stats['rendered']>0, f'No usable content briefs rendered on cards: {stats}'


def infinite_scroll_check(page):
    sentinel=page.locator('.infinite-scroll-sentinel')
    assert sentinel.count()==1, 'Infinite-scroll sentinel missing'
    before=page.locator('#news-feed .news-item').count()
    sentinel.scroll_into_view_if_needed()
    page.wait_for_function('(before)=>document.querySelectorAll("#news-feed .news-item").length>before', arg=before, timeout=5000)
    after=page.locator('#news-feed .news-item').count()
    assert after>before, f'Infinite scroll did not add stories: {before} -> {after}'


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


def synthetic_denver_without_local(page):
    return page.evaluate("""() => {
      const rows=[];
      const now=new Date().toUTCString();
      function add(title,link,state,region){
        const xml=`<item><title>${title}</title><link>${link}</link><description>${title}</description><pubDate>${now}</pubDate><source>Test Source</source><category>region</category><region>${region}</region><state>${state}</state></item>`;
        rows.push(new DOMParser().parseFromString(xml,'text/xml').documentElement);
      }
      for(let i=1;i<=6;i++)add(`Colorado statewide policy ${i}`,`https://example.com/state-only-${i}`,'Colorado','mountain');
      for(let i=1;i<=6;i++)add(`Wyoming mountain regional ${i}`,`https://example.com/regional-only-${i}`,'Wyoming','mountain');
      const result=window.__mergedStatePoolV26(rows);
      return {
        counts:window.__stateMergeCountsV26,
        tiers:result.map(i=>i.querySelector('locationTier')?.textContent||'')
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
    assert counts and counts['state']>=6 and counts['regional']>=6 and 0<=counts['local']<=6, f'Farmington State mix is invalid: {counts}'
    local_texts=page.evaluate("""() => window.__mergedStatePoolV26(allItems)
      .filter(i=>(i.querySelector('locationTier')?.textContent||'')==='Local')
      .map(i=>`${i.querySelector('title')?.textContent||''} ${i.querySelector('description')?.textContent||''}`.toLowerCase())""")
    local_terms=('farmington','san juan county','aztec','bloomfield','kirtland','shiprock','four corners')
    assert all(any(term in text for term in local_terms) for text in local_texts), f'Non-local story was labeled Local: {local_texts}'
    infinite_scroll_check(page)
    badge_checks(page)
    content_brief_checks(page)
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
    assert counts['state']==6 and counts['regional']==6 and counts['local']==6, f'Deterministic Denver State mix is not 6/6/6 with six genuine Denver stories: {synthetic}'
    assert synthetic['tiers'][:6]==['State']*6, f'First six merged stories are not State: {synthetic["tiers"]}'
    assert synthetic['tiers'][6:12]==['Regional']*6, f'Second six merged stories are not Regional: {synthetic["tiers"]}'
    assert synthetic['tiers'][12:18]==['Local']*6, f'Third six merged stories are not Local: {synthetic["tiers"]}'
    assert len(set(synthetic['links']))==18, 'Merged 6/6/6 lead mix duplicated an article'

    no_local=synthetic_denver_without_local(page)
    assert no_local['counts']['local']==0, f'State stories were relabeled Local to fill a quota: {no_local}'
    assert 'Local' not in no_local['tiers'], f'Local tier was fabricated without a Denver match: {no_local}'
    context.close()


def mobile_suite(browser):
    context=browser.new_context(viewport={'width':390,'height':844},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
    page=context.new_page();page.goto(BASE,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');page.wait_for_timeout(1200)
    assert page.locator('#tabs > .tab').count()>=15, 'Merged mobile navigation lost categories'
    assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0
    assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0
    overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
    assert overflow<=4, f'Mobile page overflows horizontally by {overflow}px'
    badge_checks(page)
    content_brief_checks(page)
    cleared=page.evaluate("""() => {
      localStorage.setItem('underreported-location-v2','{}');
      localStorage.setItem('underreported-location','Old City, NM');
      localStorage.setItem('underreported-state','NM');
      window.UnderreportedLocation.clear();
      return [
        localStorage.getItem('underreported-location-v2'),
        localStorage.getItem('underreported-location'),
        localStorage.getItem('underreported-state')
      ];
    }""")
    assert cleared==[None,None,None], f'Location clear left stale legacy keys: {cleared}'
    context.close()


def main():
    collector_checks()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        farmington_suite(browser);denver_suite(browser);mobile_suite(browser)
        browser.close()
    print('V3.1 SMOKE PASS — ranking, location, Presidential filter, NEW badges, content briefs, infinite scroll, and responsive UI.')


if __name__=='__main__':
    main()
