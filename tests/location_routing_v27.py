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
    assert 'matchesexactcity' in lower, 'Local pool must distinguish exact city from county-area matches'
    assert "['region','local'].includes(category(i))" in lower, 'Regional pool must not reuse the statewide NM pool'


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
        page.wait_for_function('window.__locationContentV36===true',timeout=10000)
        page.wait_for_timeout(1600)

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

        radius=page.evaluate('window.__locationRadiusMilesV36')
        assert radius==150, f'Expected 150-mile radius, got {radius}'
        approx=page.evaluate('window.__locationDistanceMilesV36({lat:0,lon:0},{lat:1,lon:0})')
        assert 68 < approx < 70, f'Haversine distance is incorrect: {approx}'

        # The four location filters must resolve to different ordered pools instead
        # of all repainting the same NM articles.
        pools=page.evaluate("""
        () => {
          const title=i=>i.querySelector('title')?.textContent?.trim()||'';
          const sig=fn=>fn(allItems).slice(0,8).map(title).filter(Boolean);
          return {
            state:sig(window.__locationStatePoolV36),
            county:sig(window.__locationCountyPoolV36),
            local:sig(window.__locationLocalPoolV36),
            region:sig(window.__locationRegionPoolV36),
          };
        }
        """)
        nonempty={k:v for k,v in pools.items() if v}
        assert len(nonempty)>=3, f'Too few populated location scopes: {pools}'
        signatures={k:'||'.join(v) for k,v in nonempty.items()}
        assert len(set(signatures.values()))==len(signatures), f'Location scopes returned identical feeds: {signatures}'

        # Verify clicks also repaint the visible cards, not merely the active pill.
        visible={}
        for scope in ('state','county','local','region'):
            btn=page.locator(f'.location-scope-btn[data-scope="{scope}"]')
            if not btn.count():
                continue
            btn.click();page.wait_for_timeout(220)
            titles=page.locator('#news-feed .news-item h3').all_inner_texts()[:6]
            if titles:visible[scope]='||'.join(titles)
        assert len(visible)>=3, visible
        assert len(set(visible.values()))==len(visible), f'Location buttons painted identical visible cards: {visible}'

        before=page.locator('#news-feed').inner_text()
        for _ in range(6):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(350)
        after=page.locator('#news-feed').inner_text()
        assert len(before)>100 and len(after)>100, 'News feed became blank while scrolling'
        assert page.locator('.location-scope-bar').count()==1, 'Location scope bar duplicated or disappeared'
        assert not page_errors, f'Browser errors during location scroll test: {page_errors}'

        assert page.evaluate('typeof window.__locationLocalPoolV36==="function"')
        assert page.evaluate('typeof window.__locationRegionPoolV36==="function"')
        assert page.evaluate('typeof window.__locationCountyPoolV36==="function"')
        assert page.evaluate('window.__presidentialRelevantV26===undefined'), 'Legacy browser Presidential classifier remains active'

        context.close();browser.close()


def main():
    static_checks()
    browser_checks()
    print('Location routing V36 passed: distinct state/county/local/region pools, 150-mile logic, and scroll stability.')


if __name__=='__main__':
    main()
