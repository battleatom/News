#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'

LOCATIONS={
    'NM': {'city':'Farmington','lat':36.7281,'lon':-108.2187},
    'MA': {'city':'Boston','lat':42.3601,'lon':-71.0589},
}


def region_signature(browser, state):
    loc=LOCATIONS[state]
    context=browser.new_context(viewport={'width':1280,'height':900})
    context.add_init_script(f"""
      (() => {{
        const v={{state:'{state}',city:'{loc['city']}',lat:{loc['lat']},lon:{loc['lon']},label:'{loc['city']}, {state}',source:'test',savedAt:Date.now()}};
        localStorage.setItem('underreported-location-v2',JSON.stringify(v));
        localStorage.setItem('underreported-state','{state}');
        localStorage.setItem('underreported-location','{loc['city']}, {state}');
        localStorage.removeItem('underreported-county');
      }})();
    """)
    page=context.new_page()
    errors=[]
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
    page.wait_for_function('window.__locationContentV36===true',timeout=10000)
    page.wait_for_timeout(800)
    resolved=page.evaluate("window.UnderreportedLocation.cached()")
    assert resolved and resolved.get('state')==state, resolved
    data=page.evaluate("""
      () => {
        const pool=window.__locationRegionPoolV36(allItems);
        const text=(i,n)=>(i.querySelector(n)?.textContent||'').trim();
        return pool.slice(0,20).map(i=>({
          title:text(i,'title'), state:text(i,'state'), marketState:text(i,'marketState'),
          region:text(i,'region'), tier:text(i,'locationTier')
        }));
      }
    """)
    assert not errors, errors
    assert data, f'No regional stories for {state}/{loc["city"]}'
    context.close()
    return data


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        nm=region_signature(browser,'NM')
        ma=region_signature(browser,'MA')
        browser.close()

    nm_titles={x['title'] for x in nm}
    ma_titles={x['title'] for x in ma}
    assert nm_titles != ma_titles, 'Regional feed did not change with user location'
    overlap=len(nm_titles & ma_titles)
    assert overlap <= max(1, min(len(nm_titles),len(ma_titles))//4), (overlap,nm,ma)
    assert all(x['tier']=='Southwest' for x in nm), nm
    assert all(x['tier']=='Northeast' for x in ma), ma
    print(f'LOCATION-RELATIVE REGION BROWSER TEST PASSED: Southwest={len(nm)} Northeast={len(ma)} overlap={overlap}')


if __name__=='__main__':
    main()
