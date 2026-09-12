from pathlib import Path
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'
SOURCE=Path('assets/location-content-v25.js')


def static_checks():
    s=SOURCE.read_text(encoding='utf-8')
    lower=s.lower()
    assert 'local_radius_miles=150' in lower, '150-mile local radius is missing'
    assert 'four_corners' not in lower, 'Four Corners-specific routing remains in generic location controller'
    assert 'presidential_direct' not in lower, 'Location controller still duplicates Presidential filtering'
    assert 'federal_terms' not in lower, 'Location controller still duplicates Federal filtering'
    assert "||'nm'" not in lower and "||\"nm\"" not in lower, 'Location controller still defaults users to New Mexico'
    assert "active==='nfl'" not in lower, 'Location controller must not special-case NFL'


def browser_checks():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(
            viewport={'width':1280,'height':900},
            geolocation={'latitude':36.7281,'longitude':-108.2187},
            permissions=['geolocation'],
        )
        page=context.new_page()
        page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
        page.wait_for_selector('#tabs',timeout=10000)
        page.wait_for_function('window.__locationContentV27===true',timeout=10000)
        page.wait_for_timeout(1200)

        assert page.locator('#tabs > .tab[data-nav-key="local"]').count()==1, 'Local tab should remain separate'
        assert page.locator('#tabs > .tab[data-nav-key="region"]').count()==1, 'Region tab should remain separate'
        assert page.locator('#tabs > .tab[data-nav-key="nm"]').count()==1, 'State tab should remain available'

        labels=page.locator('#tabs > .tab').all_text_contents()
        joined=' | '.join(labels)
        assert 'New Mexico' in joined or 'State' in joined, f'State label did not resolve generically: {joined}'
        assert 'Local' in joined, f'Local label missing: {joined}'
        assert 'Southwest' in joined or 'Region' in joined, f'Region label did not resolve: {joined}'

        radius=page.evaluate('window.__locationRadiusMilesV27')
        assert radius==150, f'Expected 150-mile radius, got {radius}'
        approx=page.evaluate('window.__locationDistanceMilesV27({lat:0,lon:0},{lat:1,lon:0})')
        assert 68 < approx < 70, f'Haversine distance is incorrect: {approx}'

        # The location wrapper must leave unrelated categories, including NFL, on the canonical path.
        assert page.evaluate('typeof window.__locationLocalPoolV27==="function"')
        assert page.evaluate('typeof window.__locationRegionPoolV27==="function"')
        assert page.evaluate('window.__presidentialRelevantV26===undefined'), 'Legacy browser Presidential classifier remains active'

        context.close();browser.close()


def main():
    static_checks()
    browser_checks()
    print('Location routing V27 passed: generic state/local/region personalization, 150-mile distance logic, separate tabs, no NFL special-casing.')


if __name__=='__main__':
    main()
