from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765/'


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(BASE, wait_until='domcontentloaded', timeout=30000)

        tab = page.locator('#tabs > .tab[data-nav-key="underreported"]')
        assert tab.count() == 1 and tab.is_visible(), 'Underreported tab missing'
        tab.click()
        page.wait_for_selector('#news-feed .underreported-item', timeout=10000)
        page.wait_for_timeout(300)

        rows = page.evaluate("""() => [...document.querySelectorAll('#news-feed .underreported-item')].map(card => ({
          title: card.querySelector('h3')?.textContent?.trim() || '',
          band: card.dataset.ageBand || '',
          classes: [...card.classList],
        }))""")
        assert rows, 'No Underreported cards rendered'
        assert all(row['band'] in ('blue','green','orange','purple','red') for row in rows), f'Missing feed age bands: {rows[:5]}'
        for row in rows:
            assert f"age-{row['band']}" in row['classes'], f"Age-band class mismatch: {row}"

        titles = ' '.join(row['title'].lower() for row in rows)
        for bad in ('hyrule warriors', 'gaming laptop deal', 'videos for pc'):
            assert bad not in titles, f'Low-value Tech/Gaming leakage remains: {bad}'

        # Synthetic browser regression: every server-provided age band must map to
        # its own color class, independent of the human-formatted date string.
        page.evaluate("""() => {
          const body=document.querySelector('#news-feed .section-body');
          for(const band of ['green','orange','purple','red']){
            const card=document.createElement('article');
            card.className='news-item underreported-item synthetic-age-test';
            card.dataset.ageBand=band;
            card.innerHTML='<h3>Synthetic age '+band+'</h3><div class="meta"><span>Today</span></div>';
            body.appendChild(card);
          }
        }""")
        page.wait_for_timeout(300)
        synthetic = page.evaluate("""() => [...document.querySelectorAll('.synthetic-age-test')].map(card => ({
          band: card.dataset.ageBand,
          classes: [...card.classList],
        }))""")
        assert len(synthetic) == 4
        for row in synthetic:
            assert f"age-{row['band']}" in row['classes'], f"Synthetic age color failed: {row}"

        browser.close()
    print('UNDERREPORTED UI SMOKE PASS — feed age bands, color classes and leakage guard verified.')


if __name__ == '__main__':
    main()
