from __future__ import annotations
import argparse
from playwright.sync_api import sync_playwright

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--base",default="http://127.0.0.1:8766/");parser.add_argument("--require-boxoffice",action="store_true");args=parser.parse_args()
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={"width":390,"height":844});errors=[];page.on("pageerror",lambda exc:errors.append(str(exc)));page.goto(args.base,wait_until="domcontentloaded");page.wait_for_selector("#tabs .tab")
        assert page.locator("#tabs .tab").count()>=17
        assert page.locator("#app-shell").evaluate("el=>getComputedStyle(el).position")=="sticky"
        assert page.locator("#markets").count()==1 and page.locator("#refresh-status").count()==1 and page.locator("#location-button").count()==1
        page.locator("#tabs .tab").filter(has_text="World").click();page.wait_for_selector(".story-card");initial=page.locator(".story-card").count();assert initial>0
        assert page.locator(".legend").count()==1;assert page.locator(".feedback-controls").count()>0;assert page.locator(".bookmark-btn").count()>0;assert page.get_by_text("WHY IT MATTERS").count()>0
        footer=page.locator(".feedback-controls").first;buttons=footer.locator("button");assert buttons.count()==3;assert footer.get_by_text("D · Duplicate",exact=True).count()==1;assert footer.get_by_text("NR · Not Relevant",exact=True).count()==1;assert footer.get_by_text("NW · Not Wanted",exact=True).count()==1
        dims=footer.evaluate("el=>({position:getComputedStyle(el).position,width:el.getBoundingClientRect().width,card:el.closest('.story-card').getBoundingClientRect().width})");assert dims["position"]=="static";assert dims["width"]>=dims["card"]-40
        first=buttons.nth(0).evaluate("el=>({radius:parseFloat(getComputedStyle(el).borderRadius),right:el.getBoundingClientRect().right})");second=buttons.nth(1).evaluate("el=>({left:el.getBoundingClientRect().left})");assert first["radius"]>=16;assert second["left"]>first["right"]
        bm=page.locator(".bookmark-btn").first;bm.click();page.locator("#tabs .tab").filter(has_text="Bookmarks").click();page.wait_for_timeout(150);assert page.locator(".story-card").count()>0
        page.locator("#tabs .tab").filter(has_text="Technology").click();page.wait_for_selector(".story-card");assert page.locator(".story-card").count()>0
        page.reload(wait_until="domcontentloaded");page.wait_for_selector("#tabs .tab");assert page.locator('#tabs .tab[aria-selected="true"]').filter(has_text="Technology").count()==1;assert page.locator(".story-card").count()>0
        page.locator("#tabs .tab").filter(has_text="NFL").click();page.wait_for_timeout(150);assert page.locator(".nfl-grid").count()==1
        if args.require_boxoffice:
            page.locator("#tabs .tab").filter(has_text="Box Office").click();page.wait_for_timeout(300);assert page.get_by_role("heading",name="Box Office").count()>0;assert page.locator(".movie-card").count()>0;assert page.get_by_text("Local showtimes").count()>0
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        assert not errors,errors;browser.close()
    print("V6 UX browser smoke passed.")
if __name__=="__main__":main()
