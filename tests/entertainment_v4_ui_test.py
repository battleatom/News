#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

URL='http://127.0.0.1:8765/'
MODE_KEY='underreported-entertainment-mode'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(URL,wait_until='networkidle')

    page.evaluate(f"localStorage.removeItem('{MODE_KEY}')")
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
            <entertainmentTier>ranked</entertainmentTier>
            <underreportedLinks><article><title>Jane Example named in studio labor investigation</title><link>https://example.com/under</link><source>ProPublica</source></article></underreportedLinks>
          </item>
          <item>
            <title>Actor Gossip Example dating musician after gala appearance</title>
            <link>https://example.com/ent2</link>
            <description>Actor Gossip Example is reportedly dating a musician after a gala appearance.</description>
            <pubDate>Fri, 11 Sep 2026 22:00:00 GMT</pubDate>
            <source>People</source>
            <category>entertainment</category>
            <entertainmentSafety>dirty</entertainmentSafety>
            <entertainmentLabel>PEOPLE</entertainmentLabel>
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
    assert page.locator('.entertainment-item').count()>=2, 'Dirty/default mode should show both clean and broad cards'
    toggle=page.locator('.ent-mode-toggle')
    assert toggle.count()==1, 'Clean/Dirty button missing'
    assert toggle.inner_text().strip()=='CLEAN', 'Default broad mode should offer CLEAN action'
    assert page.locator('.ent-tier.major').count()>=1, 'Major label missing'
    assert page.locator('.ent-broad-note').count()>=1, 'Broad-only card marker missing'
    foot=page.locator('.ent-underreported-links')
    assert foot.count()==1, 'Underreported connection footnote missing'
    link=foot.locator('a')
    assert link.get_attribute('href')=='https://example.com/under', 'Footnote link target incorrect'
    color=link.evaluate("el=>getComputedStyle(el).color")
    assert color in ('rgb(220, 38, 38)','rgb(220,38,38)'), f'Footnote is not red: {color}'

    # Simulate the persisted state after pressing CLEAN, then reload and verify broad cards disappear.
    page.evaluate(f"localStorage.setItem('{MODE_KEY}','clean')")
    page.reload(wait_until='networkidle')
    page.evaluate("""
    () => {
      const parser=new DOMParser();
      const xml=parser.parseFromString(`
        <rss><channel>
          <item><title>Jane Example speaks out after studio labor investigation</title><link>https://example.com/ent</link><description>Actor Jane Example discusses the studio labor investigation.</description><pubDate>Fri, 11 Sep 2026 23:00:00 GMT</pubDate><source>Variety</source><category>entertainment</category><entertainmentSafety>clean</entertainmentSafety><entertainmentLabel>MAJOR</entertainmentLabel></item>
          <item><title>Actor Gossip Example dating musician after gala appearance</title><link>https://example.com/ent2</link><description>Actor Gossip Example is reportedly dating a musician after a gala appearance.</description><pubDate>Fri, 11 Sep 2026 22:00:00 GMT</pubDate><source>People</source><category>entertainment</category><entertainmentSafety>dirty</entertainmentSafety><entertainmentLabel>PEOPLE</entertainmentLabel></item>
        </channel></rss>`, 'text/xml');
      allItems=[...allItems,...xml.querySelectorAll('item')];
      active='entertainment';
      canonicalBuildTabs();
      canonicalRender(allItems);
    }
    """)
    page.wait_for_timeout(250)
    assert page.locator('.ent-mode-toggle').inner_text().strip()=='DIRTY', 'Clean mode should offer DIRTY action'
    titles=page.locator('.entertainment-item h3').all_inner_texts()
    assert any('Jane Example' in t for t in titles), titles
    assert not any('Gossip Example' in t for t in titles), titles
    assert page.evaluate(f"localStorage.getItem('{MODE_KEY}')")=='clean', 'Mode preference did not persist'
    assert not errors, errors
    print('V4 Entertainment UI passed: persistent Clean/Dirty filtering, hierarchy labels, and red Underreported footnote verified.')
    browser.close()
