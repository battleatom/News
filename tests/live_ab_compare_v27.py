#!/usr/bin/env python3
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

MAIN='http://127.0.0.1:8766/'
BRANCH='http://127.0.0.1:8765/'
OUT=Path('live-ab-report.json')
LOCATION={
    'lat':36.7281,'lon':-108.2187,'city':'Farmington','state':'NM',
    'label':'Farmington, NM','source':'test','savedAt':9999999999999,
}

def norm_title(s):
    s=re.sub(r'\s+(?:[-–—|:]\s*)?(?:Reuters|AP News|Associated Press|BBC|CNN|Fox News|NBC News|ABC News|CBS News|NPR|USA Today|IGN|GameSpot|PC Gamer|Polygon)\s*$','',s or '',flags=re.I)
    return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()

def setup(page):
    payload=json.dumps(LOCATION)
    page.add_init_script(f"""
      localStorage.setItem('underreported-location-v2', {json.dumps(payload)});
      localStorage.setItem('underreported-location','Farmington, NM');
      localStorage.setItem('underreported-state','NM');
    """)

def tab_keys(page):
    return page.locator('#tabs > .tab').evaluate_all("els=>els.map(e=>e.dataset.navKey).filter(Boolean)")

def click_key(page,key):
    loc=page.locator(f'#tabs > .tab[data-nav-key="{key}"]')
    if loc.count()==0:return False
    loc.first.click();page.wait_for_timeout(250)
    return True

def collect_titles(page):
    # Load as much as the current UI exposes, without changing page logic.
    for _ in range(12):
        before=page.locator('#news-feed .news-item').count()
        sentinel=page.locator('#infinite-scroll-sentinel')
        if sentinel.count()==0:break
        sentinel.scroll_into_view_if_needed();page.wait_for_timeout(180)
        after=page.locator('#news-feed .news-item').count()
        if after<=before:break
    titles=[]
    for el in page.locator('#news-feed .news-item').all():
        text=''
        for sel in ('h2','h3','.title','.headline','a'):
            node=el.locator(sel)
            if node.count():
                text=node.first.inner_text().strip()
                if text:break
        if text:titles.append(text)
    return titles

def snapshot(browser,url):
    ctx=browser.new_context(viewport={'width':1440,'height':1000},geolocation={'latitude':LOCATION['lat'],'longitude':LOCATION['lon']},permissions=['geolocation'])
    page=ctx.new_page();setup(page);errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
    page.goto(url,wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('#tabs');page.wait_for_timeout(900)
    keys=tab_keys(page);data={}
    for key in keys:
        if key in {'bookmarks'}:continue
        if not click_key(page,key):continue
        titles=collect_titles(page)
        norm=[norm_title(t) for t in titles if norm_title(t)]
        dup_count=len(norm)-len(set(norm))
        data[key]={'count':len(titles),'duplicateTitles':dup_count,'titles':titles}
    ctx.close();return {'tabs':keys,'data':data,'errors':errors}

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        main=snapshot(browser,MAIN)
        branch=snapshot(browser,BRANCH)
        browser.close()
    keys=[]
    for k in main['data']:
        if k not in keys:keys.append(k)
    for k in branch['data']:
        if k not in keys:keys.append(k)
    rows=[]
    for key in keys:
        a=main['data'].get(key,{'count':0,'duplicateTitles':0,'titles':[]})
        b=branch['data'].get(key,{'count':0,'duplicateTitles':0,'titles':[]})
        aset={norm_title(x) for x in a['titles'] if norm_title(x)};bset={norm_title(x) for x in b['titles'] if norm_title(x)}
        overlap=len(aset & bset);union=len(aset | bset);jacc=round(overlap/union,3) if union else 1.0
        rows.append({'tab':key,'mainCount':a['count'],'branchCount':b['count'],'mainDuplicates':a['duplicateTitles'],'branchDuplicates':b['duplicateTitles'],'overlap':overlap,'jaccard':jacc,'onlyMain':a['titles'] if not b['titles'] else [x for x in a['titles'] if norm_title(x) not in bset],'onlyBranch':b['titles'] if not a['titles'] else [x for x in b['titles'] if norm_title(x) not in aset]})
    report={'location':LOCATION,'mainTabs':main['tabs'],'branchTabs':branch['tabs'],'mainErrors':main['errors'],'branchErrors':branch['errors'],'tabs':rows}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('LIVE A/B TAB COMPARISON')
    print('TAB             MAIN BRANCH MDUP BDUP OVERLAP SIMILARITY')
    for r in rows:
        print(f"{r['tab'][:15]:15} {r['mainCount']:4} {r['branchCount']:6} {r['mainDuplicates']:4} {r['branchDuplicates']:4} {r['overlap']:7} {r['jaccard']:10.3f}")
    print('MAIN ERRORS',len(main['errors']),main['errors'][:5])
    print('BRANCH ERRORS',len(branch['errors']),branch['errors'][:5])
    print('REPORT',OUT)

if __name__=='__main__':main()
