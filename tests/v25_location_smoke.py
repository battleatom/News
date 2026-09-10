from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'


def tab(page,key):
    return page.locator(f'#tabs > .tab[data-nav-key="{key}"]').first


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(
            viewport={'width':1600,'height':1000},
            geolocation={'latitude':39.7392,'longitude':-104.9903},
            permissions=['geolocation'],
        )
        page=context.new_page()
        page.add_init_script("""
            const now=Date.now();
            localStorage.setItem('underreported-location-v2', JSON.stringify({
              lat:39.7392,lon:-104.9903,city:'Denver',state:'CO',label:'Denver, CO',source:'device',savedAt:now
            }));
            localStorage.setItem('underreported-state','CO');
            localStorage.setItem('underreported-location','Denver, CO');
            localStorage.setItem('underreported-region','mountain');
        """)
        errors=[]
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
        page.wait_for_function("window.__locationContentV25===true",timeout=10000)
        page.wait_for_timeout(900)

        state_tab=tab(page,'nm')
        local_tab=tab(page,'local')
        assert state_tab.count() and 'Colorado' in state_tab.inner_text(), f'State tab did not become Colorado: {state_tab.inner_text() if state_tab.count() else "missing"}'
        assert local_tab.count() and 'Local / Denver' in local_tab.inner_text(), f'Local tab did not become Denver: {local_tab.inner_text() if local_tab.count() else "missing"}'

        before=page.evaluate("getComputedStyle(document.querySelector('header'),'::before')")
        before_display=page.evaluate("getComputedStyle(document.querySelector('header'),'::before').display")
        before_width=float(page.evaluate("parseFloat(getComputedStyle(document.querySelector('header'),'::before').width)"))
        after_content=page.evaluate("getComputedStyle(document.querySelector('header'),'::after').content")
        assert before_display!='none' and before_width>=100, f'Newspaper graphic missing: display={before_display} width={before_width}'
        assert 'DAILY' in after_content.upper() and 'NEWS' in after_content.upper(), f'Newspaper masthead label missing: {after_content}'

        federal=tab(page,'federal'); federal.click(); page.wait_for_timeout(400)
        federal_count=page.locator('#news-feed .news-item').count()
        federal_more=page.locator('#news-feed .load-more')
        assert federal_count==10, f'Federal first page should contain 10 stories, got {federal_count}'
        assert federal_more.count() and federal_more.first.is_visible(), 'Federal Government does not expose Load More'

        legislation=tab(page,'legislation'); legislation.click(); page.wait_for_timeout(1000)
        legislation_text=page.locator('#news-feed').inner_text()
        assert 'Colorado' in legislation_text, 'Colorado coverage/records missing from location-aware legislation view'
        legislation_more=page.locator('#news-feed .load-more')
        assert legislation_more.count() and legislation_more.first.is_visible(), 'Federal + Colorado legislation does not expose Load More'

        state_tab=tab(page,'nm'); state_tab.click(); page.wait_for_timeout(350)
        assert page.locator('#news-feed .news-item').count()>=1, 'Colorado state tab rendered no stories'
        local_tab=tab(page,'local'); local_tab.click(); page.wait_for_timeout(350)
        assert page.locator('#news-feed .news-item').count()>=1, 'Local / Denver rendered no stories'

        assert not errors, f'Page errors during Denver test: {errors[:4]}'
        print('V2.5 DENVER PASS: Colorado state tab, Local / Denver, newspaper masthead, Federal Load More and legislation Load More verified.')
        context.close();browser.close()


if __name__=='__main__':
    main()
