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

    page.goto(URL,wait_until='networkidle')
    page.evaluate(f"localStorage.removeItem('{MODE_KEY}')")
    page.goto(URL,wait_until='networkidle')
    open_entertainment(page)

    clean_pool=backing_links(page,'clean')
    dirty_pool=backing_links(page,'dirty')
    assert len(clean_pool)>=10, f'Clean backing pool too small: {len(clean_pool)}'
    assert len(dirty_pool)>=10, f'Dirty backing pool was removed: {len(dirty_pool)}'
    assert clean_pool.isdisjoint(dirty_pool), 'Clean and Dirty backing pools overlap'

    assert page.locator('.ent-mode-toggle').count()==0, 'Dirty mode button is still visible'
    assert page.locator('.ent-mode-state').count()==0, 'Clean/Dirty mode badge is still visible'
    assert page.locator('.ent-broad-note').count()==0, 'Dirty marker is visible'

    intro=page.locator('.entertainment-section .x-issues-intro').inner_text().strip()
    assert not intro.upper().startswith('CLEAN'), f'Entertainment description still starts with Clean: {intro}'

    clean_visible=visible_links(page)
    assert clean_visible, 'Entertainment feed rendered no cards'
    assert clean_visible <= clean_pool, f'Entertainment feed leaked non-clean cards: {clean_visible-clean_pool}'
    assert clean_visible.isdisjoint(dirty_pool), 'Dirty cards leaked into visible Entertainment feed'
    assert page.locator('.ent-tier').count()>=1, 'Entertainment hierarchy labels missing'

    # Dirty data and future preference plumbing remain preserved, but cannot expose the feed today.
    page.evaluate(f"localStorage.setItem('{MODE_KEY}','dirty')")
    page.goto(URL+'?entmode=dirty',wait_until='networkidle')
    open_entertainment(page)
    forced_visible=visible_links(page)
    assert forced_visible and forced_visible <= backing_links(page,'clean'), 'Dirty URL/preference exposed hidden Dirty feed'
    assert forced_visible.isdisjoint(backing_links(page,'dirty')), 'Dirty cards became visible through saved preference or URL'
    assert page.locator('.ent-mode-toggle').count()==0

    # Exercise the optional red Underreported connection independently of ranking.
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
    assert page.locator('.ent-tier.major').count()==1, 'Major label missing in Entertainment feed'
    foot=page.locator('.ent-underreported-links')
    assert foot.count()==1, 'Underreported connection footnote missing'
    link=foot.locator('a')
    assert link.get_attribute('href')=='https://example.com/under', 'Footnote link target incorrect'

    assert not errors, errors
    print('V4 Entertainment UI passed: clean feed visible, dirty controls/feed hidden, dirty backing pool preserved.')
    context.close()
    browser.close()
