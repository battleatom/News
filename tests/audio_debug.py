from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':390,'height':844})
    page=context.new_page()
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
    page.wait_for_selector('#sound-alerts-toggle',timeout=10000)
    page.wait_for_timeout(1500)
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
    page.locator('#sound-alerts-toggle').click()
    page.wait_for_timeout(300)
    count=page.evaluate('window.__testPopCount')
    stack=page.evaluate('window.__testPopStack')
    print('AUDIO DEBUG COUNT:',count)
    if stack: print('AUDIO DEBUG STACK:\n'+stack)
    browser.close()
