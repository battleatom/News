from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'

def click_key(page,key):
    tab=page.locator(f'#tabs > .tab[data-nav-key="{key}"]')
    assert tab.count()==1 and tab.is_visible(), f'Missing tab {key}'
    tab.click(); page.wait_for_timeout(350)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':390,'height':844},geolocation={'latitude':36.7281,'longitude':-108.2187},permissions=['geolocation'])
        page=context.new_page(); errors=[]; page.on('pageerror',lambda exc: errors.append(str(exc)))
        page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
        page.wait_for_selector('#tabs'); page.wait_for_timeout(1600)

        assert page.evaluate('window.__alertsNewV282===true'), 'V2.8.2 NEW/audio gate missing'
        assert page.evaluate('window.__loadMoreRevealOnlyV282===true'), 'Reveal-only Load More controller missing'
        assert page.evaluate('window.__locationDedupeV281===true'), 'State event dedupe controller missing'

        now=page.evaluate('Date.now()')
        classify=lambda hours: page.evaluate('([p,n])=>window.__classifyNewBadgeV26(p,0,n)',[now-hours*3600000,now])
        assert classify(.25)=='red'; assert classify(.99)=='red'; assert classify(1.01)=='blue'
        assert classify(2.99)=='blue'; assert classify(3.01)=='yellow'; assert classify(5.99)=='yellow'; assert classify(6.01)==''

        click_key(page,'nm')
        synthetic=page.evaluate("""() => {
          const now=new Date().toUTCString();
          function item(title,link,cat='nm'){
            const xml=`<item><title>${title}</title><link>${link}</link><description>${title}</description><pubDate>${now}</pubDate><source>Test</source><category>${cat}</category><state>New Mexico</state><region>southwest</region></item>`;
            return new DOMParser().parseFromString(xml,'text/xml').documentElement;
          }
          const rows=[item('Farmington school board approves new budget','https://a.example/1'),item('New budget approved by Farmington school board','https://b.example/2'),item('Farmington hospital opens new emergency wing','https://c.example/3'),item('New emergency wing opens at Farmington hospital','https://d.example/4'),item('New Mexico governor signs water bill','https://e.example/5')];
          return window.__mergedStatePoolV26(rows).map(i=>i.querySelector('title')?.textContent||'');
        }""")
        lower=[x.lower() for x in synthetic]
        assert sum('school board' in x and 'budget' in x for x in lower)==1, synthetic
        assert sum('hospital' in x and 'emergency wing' in x for x in lower)==1, synthetic

        load_more_checked=False
        for key in ('world','us','technology','nm','federal'):
            click_key(page,key); page.wait_for_timeout(250)
            more=page.locator('.load-more')
            if more.count() and more.first.is_visible():
                page.evaluate('window.scrollTo(0, Math.max(400, document.body.scrollHeight-900))'); page.wait_for_timeout(100)
                before=page.evaluate('window.scrollY')
                visible_before=page.locator('#news-feed .news-item:not([data-page-hidden="true"])').count()
                total_before=page.locator('#news-feed .news-item').count()
                more.first.click(); page.wait_for_timeout(250)
                after=page.evaluate('window.scrollY')
                visible_after=page.locator('#news-feed .news-item:not([data-page-hidden="true"])').count()
                total_after=page.locator('#news-feed .news-item').count()
                assert visible_after>visible_before, f'Load More revealed nothing in {key}'
                assert total_after==total_before, f'Load More rerendered/rebuilt cards in {key}'
                assert abs(after-before)<=5, f'Load More changed scroll in {key}: {before} -> {after}'
                load_more_checked=True; break
        assert load_more_checked, 'No category exposed Load More for scroll test'

        click_key(page,'top')
        assert page.locator('#refresh').is_visible(), 'Top Stories refresh button missing'
        sound=page.locator('#sound-alerts-toggle'); assert sound.is_visible(), 'Sound button missing'
        page.evaluate("localStorage.setItem('underreported-sound-alerts-v2','off')")
        sound.click(); page.wait_for_timeout(250)
        assert page.evaluate("localStorage.getItem('underreported-sound-alerts-v2')==='on'"), 'Sound button did not enable/persist alerts'
        assert 'Alerts on' in page.locator('#sound-alerts-toggle').inner_text(), 'Sound button UI did not reflect enabled state'
        page.locator('#sound-alerts-toggle').click(); page.wait_for_timeout(150)
        assert page.evaluate("localStorage.getItem('underreported-sound-alerts-v2')==='off'"), 'Sound button did not toggle off'

        assert not errors, f'Browser errors: {errors[:5]}'
        context.close(); browser.close()
    print('V2.8.2 PASS — reveal-only pagination, single-owner sound toggle, publish-age badges, and NM dedupe.')


if __name__=='__main__':
    main()
