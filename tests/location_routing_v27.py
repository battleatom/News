from pathlib import Path
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'
SOURCE=Path('assets/location-content-v25.js')


def static_checks():
    s=SOURCE.read_text(encoding='utf-8')
    lower=s.lower()
    assert 'local_radius_miles=150' in lower, '150-mile local radius is missing'
    assert 'presidential_direct' not in lower, 'Location controller still duplicates Presidential filtering'
    assert 'federal_terms' not in lower, 'Location controller still duplicates Federal filtering'
    assert "||'nm'" not in lower and "||\"nm\"" not in lower, 'Location controller still defaults users to New Mexico'
    assert "active==='nfl'" not in lower, 'Location controller must not special-case NFL'
    assert 'locationscope' not in lower or 'scope_key' in lower
    assert "observer.observe(root,{childlist:true})" in lower, 'Location observer must not watch the full subtree'
    assert 'bar.innerhtml!==next' in lower, 'Location scope bar must avoid idempotent DOM rewrites'


def browser_checks():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(
            viewport={'width':1280,'height':900},
            geolocation={'latitude':36.7281,'longitude':-108.2187},
            permissions=['geolocation'],
        )
        page=context.new_page()
        page_errors=[]
        page.on('pageerror', lambda exc: page_errors.append(str(exc)))
        page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
        page.wait_for_selector('#tabs',timeout=10000)
        page.wait_for_function('window.__locationContentV35===true',timeout=10000)
        page.wait_for_timeout(1400)

        # Local and Region are now nested under the user's state hub.
        assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==0, 'Local should not remain a top-level tab'
        assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==0, 'Region should not remain a top-level tab'
        state_tab=page.locator('#tabs > .tab[data-nav-key="nm"]')
        assert state_tab.count()==1, 'User state tab should remain available'
        assert 'New Mexico' in state_tab.inner_text() or 'State' in state_tab.inner_text()

        state_tab.click()
        page.wait_for_selector('.location-scope-bar',timeout=10000)
        scope_labels=page.locator('.location-scope-bar .location-scope-btn').all_text_contents()
        joined=' | '.join(scope_labels)
        assert 'All' in joined and 'Statewide' in joined, f'Missing state hub scopes: {joined}'
        assert 'Farmington' in joined or 'Local' in joined, f'Missing local scope: {joined}'
        assert 'Southwest' in joined or 'Region' in joined, f'Missing regional scope: {joined}'
        assert 'San Juan County' in joined or 'County' in joined, f'Missing county scope: {joined}'

        radius=page.evaluate('window.__locationRadiusMilesV35')
        assert radius==150, f'Expected 150-mile radius, got {radius}'
        approx=page.evaluate('window.__locationDistanceMilesV35({lat:0,lon:0},{lat:1,lon:0})')
        assert 68 < approx < 70, f'Haversine distance is incorrect: {approx}'

        # Reproduce the mobile failure mode: repeated scroll/load-more mutations must
        # not create a MutationObserver render loop or blank the application.
        before=page.locator('#news-feed').inner_text()
        for _ in range(6):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(350)
        after=page.locator('#news-feed').inner_text()
        assert len(before)>100 and len(after)>100, 'News feed became blank while scrolling'
        assert page.locator('.location-scope-bar').count()==1, 'Location scope bar duplicated or disappeared'
        assert not page_errors, f'Browser errors during location scroll test: {page_errors}'

        assert page.evaluate('typeof window.__locationLocalPoolV35==="function"')
        assert page.evaluate('typeof window.__locationRegionPoolV35==="function"')
        assert page.evaluate('typeof window.__locationCountyPoolV35==="function"')
        assert page.evaluate('window.__presidentialRelevantV26===undefined'), 'Legacy browser Presidential classifier remains active'

        context.close();browser.close()


def main():
    static_checks()
    browser_checks()
    print('Location routing V35 passed: state hub, county/local/region scopes, 150-mile logic, and scroll stability.')


if __name__=='__main__':
    main()
