from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765/'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1600, 'height': 1000})
    page.goto(BASE, wait_until='domcontentloaded', timeout=30000)
    page.wait_for_selector('.container', timeout=10000)
    page.wait_for_timeout(500)

    viewport = page.evaluate('window.innerWidth')
    width = page.locator('.container').first.evaluate('el => el.getBoundingClientRect().width')
    max_width = page.locator('.container').first.evaluate('el => getComputedStyle(el).maxWidth')

    assert viewport - width <= 60, f'Desktop container is still capped: viewport={viewport}, container={width}'
    assert max_width == 'none', f'Desktop container max-width should be none, got {max_width}'

    # Mobile behavior should remain naturally viewport-bound.
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(250)
    mobile_width = page.locator('.container').first.evaluate('el => el.getBoundingClientRect().width')
    assert mobile_width <= 390, f'Mobile container overflowed viewport: {mobile_width}'

    browser.close()

print('DESKTOP WIDTH PASS')
