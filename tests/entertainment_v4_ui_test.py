#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

URL='http://127.0.0.1:8765/'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(URL,wait_until='networkidle')

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
            <entertainmentTier>newest</entertainmentTier>
            <underreportedLinks><article><title>Jane Example named in studio labor investigation</title><link>https://example.com/under</link><source>ProPublica</source></article></underreportedLinks>
          </item>
          <item>
            <title>Music Artist Example announces independent benefit project</title>
            <link>https://example.com/ent2</link>
            <description>Musician Artist Example announces an independent music project.</description>
            <pubDate>Fri, 11 Sep 2026 22:00:00 GMT</pubDate>
            <source>Billboard</source>
            <category>entertainment</category>
            <entertainmentTier>under-the-radar</entertainmentTier>
          </item>
        </channel></rss>`, 'text/xml');
      const injected=[...xml.querySelectorAll('item')];
      allItems=[...allItems,...injected];
      active='entertainment';
      canonicalBuildTabs();
      canonicalRender(allItems);
    }
    """)
    page.wait_for_timeout(250)

    tab=page.locator('#tabs button',has_text='Entertainment')
    assert tab.count()==1, 'Entertainment tab missing'
    assert page.locator('.entertainment-item').count()>=2, 'Entertainment cards did not render'
    assert page.locator('.ent-tier.newest').count()>=1, 'Newest label missing'
    assert page.locator('.ent-tier.radar').count()>=1, 'Under-the-radar label missing'
    foot=page.locator('.ent-underreported-links')
    assert foot.count()==1, 'Underreported connection footnote missing'
    link=foot.locator('a')
    assert link.get_attribute('href')=='https://example.com/under', 'Footnote link target incorrect'
    color=link.evaluate("el=>getComputedStyle(el).color")
    assert color in ('rgb(220, 38, 38)','rgb(220,38,38)'), f'Footnote is not red: {color}'
    assert not errors, errors
    print('V4 Entertainment UI passed: tab, newest/under-the-radar labels, and red Underreported footnote link verified.')
    browser.close()
