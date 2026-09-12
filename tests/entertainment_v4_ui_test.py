#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

URL='http://127.0.0.1:8765/'
MODE_KEY='underreported-entertainment-mode'


def backing_links(page, safety):
    return set(page.evaluate(
        """safety => [...allItems]
          .filter(i => (i.querySelector('category')?.textContent?.trim()||'') === 'entertainment')
          .filter(i => (i.querySelector('entertainmentSafety')?.textContent?.trim()||'clean').toLowerCase() === safety)
          .map(i => i.querySelector('link')?.textContent?.trim()||'')
          .filter(Boolean)
        """,
        safety,
    ))


def visible_links(page):
    return set(page.locator('.entertainment-item h3 a').evaluate_all(
        "els => els.map(a => a.href).filter(Boolean)"
    ))


def open_entertainment(page):
    tab=page.locator('#tabs button',has_text='Entertainment')
    assert tab.count()==1, 'Entertainment tab missing'
    tab.click()
    page.wait_for_selector('.entertainment-section',timeout=10000)
    page.wait_for_timeout(200)


with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':1280,'height':900})
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))

    # Start from the default broad/Dirty mode with no saved preference.
    page.goto(URL,wait_until='networkidle')
    page.evaluate(f"localStorage.removeItem('{MODE_KEY}')")
    page.goto(URL,wait_until='networkidle')
    open_entertainment(page)

    clean_pool=backing_links(page,'clean')
    dirty_pool=backing_links(page,'dirty')
    assert len(clean_pool)>=10, f'Clean backing pool too small: {len(clean_pool)}'
    assert len(dirty_pool)>=10, f'Dirty backing pool too small: {len(dirty_pool)}'
    assert clean_pool.isdisjoint(dirty_pool), 'Clean and Dirty backing pools overlap'

    toggle=page.locator('.ent-mode-toggle')
    assert toggle.count()==1, 'Clean/Dirty button missing'
    assert toggle.inner_text().strip()=='CLEAN', 'Default Dirty mode should offer CLEAN action'
    assert page.locator('.ent-mode-state').inner_text().strip()=='DIRTY MODE'

    dirty_visible=visible_links(page)
    assert dirty_visible, 'Dirty mode rendered no cards'
    assert dirty_visible <= dirty_pool, f'Dirty mode leaked non-Dirty cards: {dirty_visible-dirty_pool}'
    assert dirty_visible.isdisjoint(clean_pool), 'Clean cards leaked into Dirty mode'
    assert page.locator('.ent-broad-note').count()==len(dirty_visible), 'Dirty card marker missing'

    # Use the real control. It must persist mode and force a reload into an exclusive Clean feed.
    with page.expect_navigation(wait_until='networkidle'):
        toggle.click()
    open_entertainment(page)
    assert page.locator('.ent-mode-toggle').inner_text().strip()=='DIRTY', 'Clean mode should offer DIRTY action'
    assert page.locator('.ent-mode-state').inner_text().strip()=='CLEAN MODE'
    assert page.evaluate(f"localStorage.getItem('{MODE_KEY}')")=='clean', 'Clean mode preference did not persist'

    clean_pool_after=backing_links(page,'clean')
    dirty_pool_after=backing_links(page,'dirty')
    clean_visible=visible_links(page)
    assert clean_visible, 'Clean mode rendered no cards'
    assert clean_visible <= clean_pool_after, f'Clean mode leaked non-Clean cards: {clean_visible-clean_pool_after}'
    assert clean_visible.isdisjoint(dirty_pool_after), 'Dirty cards leaked into Clean mode'
    assert clean_visible != dirty_visible, 'Clean and Dirty rendered the same first-page cards'
    assert page.locator('.ent-broad-note').count()==0, 'Dirty marker appeared in Clean mode'
    assert page.locator('.ent-tier').count()>=1, 'Entertainment hierarchy labels missing'

    # Persistence must survive a fresh navigation without the entmode URL parameter.
    page.goto(URL,wait_until='networkidle')
    open_entertainment(page)
    assert page.locator('.ent-mode-state').inner_text().strip()=='CLEAN MODE', 'Saved Clean mode did not survive refresh/navigation'
    persisted_visible=visible_links(page)
    persisted_clean_pool=backing_links(page,'clean')
    assert persisted_visible and persisted_visible <= persisted_clean_pool

    # Exercise the optional red Underreported connection independently of ranking.
    # This isolates presentation behavior from the real feed's editorial order.
    page.evaluate("""
    () => {
      const parser=new DOMParser();
      const xml=parser.parseFromString(`
        <rss><channel>
          <item>
            <title>Jane Example speaks out after studio labor investigation</title>
            <link>https://example.com/ent</link>
            <description>Actor Jane Example discusses the studio labor investigation.</description>
            <pubDate>Fri, 11 Sep 2026 23:00:00 GMT</pubDate>
            <source>Variety</source>
            <category>entertainment</category>
            <entertainmentSafety>clean</entertainmentSafety>
            <entertainmentLabel>MAJOR</entertainmentLabel>
            <entertainmentScore>999</entertainmentScore>
            <entertainmentTier>ranked</entertainmentTier>
            <underreportedLinks>
              <article>
                <title>Jane Example named in studio labor investigation</title>
                <link>https://example.com/under</link>
                <source>ProPublica</source>
              </article>
            </underreportedLinks>
          </item>
        </channel></rss>`, 'text/xml');
      allItems=[...xml.querySelectorAll('item')];
      active='entertainment';
      if(typeof loadCounts!=='undefined')loadCounts.entertainment=10;
      canonicalRender(allItems);
    }
    """)
    page.wait_for_timeout(150)
    assert page.locator('.ent-tier.major').count()==1, 'Major label missing in Clean mode'
    foot=page.locator('.ent-underreported-links')
    assert foot.count()==1, 'Underreported connection footnote missing'
    link=foot.locator('a')
    assert link.get_attribute('href')=='https://example.com/under', 'Footnote link target incorrect'
    color=link.evaluate("el=>getComputedStyle(el).color")
    assert color in ('rgb(220, 38, 38)','rgb(220,38,38)'), f'Footnote is not red: {color}'

    assert not errors, errors
    print(
        'V4 Entertainment UI passed: real mutually exclusive Clean/Dirty pools, '
        'persistent mode switching, hierarchy labels, and red Underreported footnote verified.'
    )
    context.close()
    browser.close()
