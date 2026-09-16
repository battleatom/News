from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DIST=ROOT/"dist"
REQUIRED_FEATURE_MARKERS={
 "sticky_shell":"id=\"app-shell\"","markets":"id=\"markets\"","tabs":"id=\"tabs\"","location":"id=\"location-button\"","auto_refresh":"id=\"refresh-status\"",
 "bookmarks":"data-bookmark","feedback":"data-feedback","why_matters":"WHY IT MATTERS","related":"Coverage ·","nfl":"nfl-live-center","boxoffice":"Local showtimes","legislation":"OFFICIAL SOURCE","underreported":"Underreported"
}
def fail(errors:list[str])->None:
    for error in errors:print("ERROR:",error)
    raise SystemExit(f"V6 audit failed with {len(errors)} error(s).")
def main()->None:
    errors=[];required=["index.html","styles.css","app.js","store.js","renderers.js","location.js","feedback.js","feed.json","nfl.json","boxoffice.json","markets.json","status.json"]
    for name in required:
        if not(DIST/name).exists():errors.append(f"missing build artifact: {name}")
    if errors:fail(errors)
    html=(DIST/"index.html").read_text(encoding="utf-8");css=(DIST/"styles.css").read_text(encoding="utf-8");runtime="\n".join((DIST/name).read_text(encoding="utf-8") for name in ("app.js","store.js","renderers.js","location.js","feedback.js"))
    if "MutationObserver" in runtime:errors.append("runtime must not use MutationObserver")
    if "canonicalRender" in runtime:errors.append("legacy canonicalRender ownership leaked into V6")
    if "patch_" in runtime+html:errors.append("legacy patch architecture leaked into V6 runtime")
    if "position:sticky" not in css.replace(" ",""):errors.append("sticky shell CSS is missing")
    if html.count('id="app-shell"')!=1:errors.append("expected exactly one app shell")
    if html.count('id="tabs"')!=1 or html.count('id="feed"')!=1:errors.append("required navigation/feed roots are not unique")
    search=html+runtime
    for feature,marker in REQUIRED_FEATURE_MARKERS.items():
        if marker not in search:errors.append(f"UX parity marker missing: {feature}")
    feed=json.loads((DIST/"feed.json").read_text(encoding="utf-8"));categories=feed.get("categories",{});stories=feed.get("stories",{})
    if set(categories)!=set(stories):errors.append("feed category metadata and story pools differ")
    ids=[]
    for cat,rows in stories.items():
        seen=set()
        for row in rows:
            sid=row.get("id");url=row.get("url","")
            if not sid:errors.append(f"{cat}: story without id")
            ids.append(sid)
            if url in seen:errors.append(f"{cat}: duplicate url remains: {url}")
            seen.add(url)
    if len(ids)!=len(set(ids)):errors.append("story ids are not globally unique")
    if errors:fail(errors)
    print("V6 audit passed: standalone engine, single UX shell, no legacy runtime, parity markers present, clean story pools.")
if __name__=="__main__":main()
