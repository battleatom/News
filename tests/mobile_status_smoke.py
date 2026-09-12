from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765/'


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 390, 'height': 844},
            geolocation={'latitude': 36.7281, 'longitude': -108.2187},
            permissions=['geolocation'],
        )
        page = context.new_page()
        page.goto(BASE, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_selector('#v3-auto-status', state='attached', timeout=10000)
        page.wait_for_function("""() => {
          const el=document.getElementById('v3-auto-status');
          return el && el.offsetParent!==null && el.dataset.fetched && el.dataset.countdown;
        }""", timeout=10000)

        status = page.locator('#v3-auto-status')
        assert status.is_visible(), 'Mobile automatic-update status is hidden'
        first = status.inner_text().strip()
        assert 'fetched' in first.lower(), f'Mobile fetch count is missing: {first}'
        assert any(word in first.lower() for word in ('auto update', 'checking', 'retrying', 'update delayed')), f'Mobile auto-update state is missing: {first}'

        # Startup performs a real feed refresh and several status/stat synchronizations.
        # Wait until the deadline itself has stopped moving before judging the visual
        # countdown. This tests the user-visible timer rather than racing startup state.
        page.wait_for_function("""() => {
          const text=document.getElementById('status')?.textContent||'';
          const finished=/stories fetched|refresh unavailable|update failed/i.test(text);
          return finished && !window.pullInProgress && Number(window.nextScheduledPull)>Date.now();
        }""", timeout=15000)
        page.wait_for_timeout(1200)

        countdown1 = status.get_attribute('data-countdown') or ''
        target1 = page.evaluate('Number(window.nextScheduledPull)||0')
        assert countdown1 and ('m' in countdown1 or 'h' in countdown1), f'Mobile countdown is missing: {countdown1}'

        # A one-second display may be sampled immediately after a tick. Poll for up to
        # three seconds so the assertion proves that it is live without depending on
        # the interval phase at the instant Playwright captured countdown1.
        page.wait_for_function("""before => {
          const el=document.getElementById('v3-auto-status');
          return el && el.dataset.countdown && el.dataset.countdown!==before;
        }""", arg=countdown1, timeout=3500)
        countdown2 = status.get_attribute('data-countdown') or ''
        target2 = page.evaluate('Number(window.nextScheduledPull)||0')
        assert abs(target2-target1) < 100, f'Countdown deadline unexpectedly moved after initial refresh: {target1} -> {target2}'
        assert countdown2 and countdown2 != countdown1, f'Mobile countdown is not live: {countdown1} -> {countdown2}'

        local = page.locator('#local-status')
        assert local.count() == 1 and local.is_visible(), 'Time/weather status disappeared while restoring update status'

        overflow = page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
        assert overflow <= 4, f'Mobile utility bar introduced horizontal overflow: {overflow}px'

        context.close()
        browser.close()
    print('MOBILE STATUS SMOKE PASS — auto update, fetched count, live countdown, time/weather, and width verified.')


if __name__ == '__main__':
    main()
