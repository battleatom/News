from playwright.sync_api import sync_playwright

URL='http://127.0.0.1:8765/'
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':390,'height':844})
    page.goto(URL,wait_until='networkidle')
    sh=page.locator('#system-health')
    sh.wait_for(state='visible')
    dot=sh.locator('.sh-dot')
    assert dot.is_visible()
    button=sh.locator('.sh-button')
    assert button.get_attribute('aria-expanded')=='false'
    button.click()
    panel=sh.locator('.sh-panel')
    assert panel.is_visible()
    assert button.get_attribute('aria-expanded')=='true'
    text=panel.inner_text()
    assert 'SYSTEM HEALTH' in text
    assert 'fetched' in text
    assert panel.locator('.sh-system').count() >= 1
    page.keyboard.press('Tab')
    page.locator('header').click()
    assert panel.is_hidden()
    browser.close()
print('System Health mobile browser smoke passed.')
