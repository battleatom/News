from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':390,'height':844})
    page=context.new_page()
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
    page.wait_for_selector('#sound-alerts-toggle',timeout=10000)
    page.wait_for_timeout(1500)

    # Freeze automatic refresh activity so this test measures only the alert gate.
    page.evaluate("""() => {
      try{clearTimeout(window.__autoRefreshTimeout)}catch(e){}
      window.nextScheduledPull=Date.now()+60*60*1000;
      window.__testPopCount=0;
      window.__testPopStack='';
      window.playNewArticlePop=()=>{
        window.__testPopCount++;
        window.__testPopStack=(new Error('playNewArticlePop called')).stack||'';
        return true;
      };
    }""")

    # Enabling alerts is only permission/unlock; it must be silent.
    page.locator('#sound-alerts-toggle').click()
    page.wait_for_timeout(300)
    count=page.evaluate('window.__testPopCount')
    stack=page.evaluate('window.__testPopStack')
    assert count == 0, f'Enabling sound emitted audio unexpectedly:\n{stack}'
    assert page.evaluate("localStorage.getItem('underreported-sound-alerts-v2')==='on'"), 'Sound preference did not persist'

    # The legacy numeric count is never sufficient to make sound.
    page.evaluate('window.__queueNewArticlePopV23(1)')
    assert page.evaluate('window.__testPopCount') == 0, 'Legacy numeric new-count emitted audio'

    # The final V2.3 gate is driven only by verified new links.
    page.evaluate('window.__playVerifiedNewV23(0)')
    assert page.evaluate('window.__testPopCount') == 0, 'Zero verified new links emitted audio'
    page.evaluate('window.__playVerifiedNewV23(1)')
    assert page.evaluate('window.__testPopCount') == 1, 'Verified new link did not emit exactly one alert'

    print('AUDIO ALERT PASS: opt-in silent; sound fires only for verified new-link event.')
    browser.close()
