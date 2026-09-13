from __future__ import annotations

import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

PORT = 8765
URL = f'http://127.0.0.1:{PORT}/index.html'

server = subprocess.Popen(
    [sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    for _ in range(40):
        try:
            urllib.request.urlopen(URL, timeout=0.5).read(32)
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise SystemExit('Local test server did not start')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 390, 'height': 844})
        errors = []
        page.on('pageerror', lambda exc: errors.append(f'pageerror: {exc}'))
        page.on('console', lambda msg: errors.append(f'console {msg.type}: {msg.text}') if msg.type == 'error' else None)
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_selector('#tabs .tab', timeout=10000)
        page.wait_for_timeout(500)

        tabs = page.locator('#tabs .tab')
        labels = [tabs.nth(i).inner_text() for i in range(tabs.count())]
        print('Tab labels:', labels)
        print('App V2 loaded:', page.evaluate('Boolean(window.__underreportedV2)'))
        print('Script sources:', page.evaluate("[...document.scripts].map(s=>s.src).filter(Boolean)"))
        if errors:
            print('Browser errors:', errors)

        region = page.locator('#tabs .tab').filter(has_text='Region')
        cue = page.locator('#tab-scroll-cue-v2')
        assert region.count() == 1, f'Exactly one Regional tab must exist; labels={labels!r}'
        assert cue.count() == 1, f'Mobile Regional navigation cue was not created; browser_errors={errors!r}'
        assert cue.is_visible(), 'Mobile Regional navigation cue must be visible when Region is off-screen'
        assert 'Region' in cue.inner_text(), 'Cue must explicitly identify the Regional tab while it is off-screen'

        cue.click()
        page.wait_for_timeout(450)
        visible = page.evaluate('''() => {
          const tabs=document.getElementById('tabs');
          const region=[...tabs.querySelectorAll('.tab')].find(b=>/Region/i.test(b.textContent));
          if(!region)return false;
          const tr=tabs.getBoundingClientRect(), rr=region.getBoundingClientRect();
          return rr.left >= tr.left - 2 && rr.right <= tr.right + 2;
        }''')
        assert visible, 'Regional tab did not become visible after using the mobile cue'

        region.click()
        page.wait_for_timeout(250)
        assert region.get_attribute('aria-current') == 'page', 'Regional tab did not become active after click'
        assert page.locator('body').get_attribute('data-active-tab') == 'region', 'Regional feed did not become the active view'
        browser.close()

    print('Mobile Regional tab browser reachability passed.')
finally:
    server.terminate()
    try:
        server.wait(timeout=3)
    except subprocess.TimeoutExpired:
        server.kill()
