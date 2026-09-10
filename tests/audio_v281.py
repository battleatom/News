from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':390,'height':844})
    page=context.new_page()
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
    page.wait_for_selector('#sound-alerts-toggle',timeout=10000)
    page.wait_for_timeout(1200)

    page.evaluate("""() => {
      window.__testPopCount=0;
      window.playNewArticlePop=()=>{window.__testPopCount++;return true};
      localStorage.removeItem('underreported-audio-alerted-v281');
    }""")

    # Enabling sound should give one immediate confirmation chime and persist.
    page.locator('#sound-alerts-toggle').click(); page.wait_for_timeout(250)
    assert page.evaluate("localStorage.getItem('underreported-sound-alerts-v2')==='on'")
    assert page.evaluate('window.__testPopCount')==1, 'Sound enable did not produce confirmation audio'

    # Inject three known publication ages into allItems and exercise the fresh gate.
    result=page.evaluate("""() => {
      function add(title,link,minutes){
        const d=new Date(Date.now()-minutes*60000).toUTCString();
        const xml=`<item><title>${title}</title><link>${link}</link><description>${title}</description><pubDate>${d}</pubDate><source>Test</source><category>top</category></item>`;
        allItems.push(new DOMParser().parseFromString(xml,'text/xml').documentElement);
      }
      add('Fresh alert candidate','https://example.com/fresh-audio',10);
      add('Too old for audio','https://example.com/old-audio',31);
      add('Also fresh','https://example.com/fresh-audio-2',20);
      return {
        fresh10:window.__freshPublishedLinksV281(['https://example.com/fresh-audio']).length,
        old31:window.__freshPublishedLinksV281(['https://example.com/old-audio']).length,
        freshPair:window.__freshPublishedLinksV281(['https://example.com/fresh-audio','https://example.com/fresh-audio-2']).length
      };
    }""")
    assert result['fresh10']==1
    assert result['old31']==0
    assert result['freshPair']==2

    # One refresh/event with multiple fresh stories produces exactly one chime.
    page.evaluate("window.__playFreshPublishedAlertV281(['https://example.com/fresh-audio','https://example.com/fresh-audio-2'])")
    assert page.evaluate('window.__testPopCount')==2, 'Fresh article event did not produce one alert chime'

    # Replaying the same links must not chime again.
    page.evaluate("window.__playFreshPublishedAlertV281(['https://example.com/fresh-audio','https://example.com/fresh-audio-2'])")
    assert page.evaluate('window.__testPopCount')==2, 'Same articles triggered audio more than once'

    # >30 minute article must not trigger.
    page.evaluate("window.__playFreshPublishedAlertV281(['https://example.com/old-audio'])")
    assert page.evaluate('window.__testPopCount')==2, 'Article older than 30 minutes triggered audio'

    print('V2.8.1 AUDIO PASS — enable confirmation works; fresh <=30m articles chime once only.')
    browser.close()
