from __future__ import annotations
import argparse
from playwright.sync_api import sync_playwright

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--base",default="http://127.0.0.1:8766/");parser.add_argument("--require-boxoffice",action="store_true");args=parser.parse_args()
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={"width":390,"height":844});errors=[];page.on("pageerror",lambda exc: errors.append(str(exc)));page.goto(args.base,wait_until="networkidle");page.wait_for_selector("#tabs .tab");assert page.locator("#tabs .tab").count()>=16;assert page.locator("#app-shell").evaluate("el=>getComputedStyle(el).position")=="sticky";page.locator("#tabs .tab").filter(has_text="World").click();page.wait_for_selector(".story-card");initial=page.locator(".story-card").count();assert initial>0,initial;button=page.get_by_role("button",name="Show more stories");
        if button.count():
            before=page.locator(".story-card").count();button.click();assert page.locator(".story-card").count()>=before
        page.locator("#tabs .tab").filter(has_text="Technology").click();page.wait_for_selector(".story-card");assert page.locator(".story-card").count()>0
        if args.require_boxoffice:
            page.locator("#tabs .tab").filter(has_text="Box Office").click();page.wait_for_timeout(300);assert page.locator(".movie-card").count()>0
        assert not errors,errors;browser.close()
    print("V6 browser smoke passed.")
if __name__=="__main__": main()
