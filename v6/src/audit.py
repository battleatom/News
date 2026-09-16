from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];DIST=ROOT/"dist"

def fail(errors:list[str]) -> None:
    for error in errors: print("ERROR:",error)
    raise SystemExit(f"V6 audit failed with {len(errors)} error(s).")

def main() -> None:
    errors=[];required=["index.html","styles.css","app.js","store.js","renderers.js","location.js","feedback.js","feed.json","nfl.json","boxoffice.json","status.json"]
    for name in required:
        if not (DIST/name).exists(): errors.append(f"missing build artifact: {name}")
    if errors: fail(errors)
    html=(DIST/"index.html").read_text(encoding="utf-8");app=(DIST/"app.js").read_text(encoding="utf-8");renderers=(DIST/"renderers.js").read_text(encoding="utf-8");css=(DIST/"styles.css").read_text(encoding="utf-8")
    runtime="".join((app,renderers,(DIST/"store.js").read_text(),(DIST/"feedback.js").read_text(),(DIST/"location.js").read_text()))
    if "MutationObserver" in runtime: errors.append("runtime must not use MutationObserver")
    if "canonicalRender" in app+renderers: errors.append("legacy canonicalRender ownership leaked into V6")
    if "patch_" in app+renderers+html: errors.append("legacy patch architecture leaked into V6 runtime")
    if "position:sticky" not in css.replace(" ",""): errors.append("sticky shell CSS is missing")
    if html.count('id="app-shell"')!=1: errors.append("expected exactly one app shell")
    if html.count('id="tabs"')!=1 or html.count('id="feed"')!=1: errors.append("required navigation/feed roots are not unique")
    feed=json.loads((DIST/"feed.json").read_text(encoding="utf-8"));categories=feed.get("categories",{});stories=feed.get("stories",{})
    if set(categories)!=set(stories): errors.append("feed category metadata and story pools differ")
    ids=[]
    for cat,rows in stories.items():
        seen=set()
        for row in rows:
            sid=row.get("id")
            if not sid: errors.append(f"{cat}: story without id")
            ids.append(sid);url=row.get("url","")
            if url in seen: errors.append(f"{cat}: duplicate url remains: {url}")
            seen.add(url)
    if len(ids)!=len(set(ids)): errors.append("story ids are not globally unique")
    if errors: fail(errors)
    print("V6 audit passed: single shell, single renderer architecture, no MutationObserver, no legacy canonicalRender, clean category pools.")

if __name__=="__main__": main()
