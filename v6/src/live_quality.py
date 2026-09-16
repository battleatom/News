from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/"dist"/"status.json"
BOX=ROOT/"dist"/"boxoffice.json"

REQUIRED_NONEMPTY={"top","nfl","underreported","world","us","presidential","federal","legislation","nm","local","region","technology","gaming","military","entertainment"}
MIN_TOTAL=120
MAX_ERROR_RATIO=0.35

def main() -> None:
    status=json.loads(STATUS.read_text(encoding="utf-8"));counts=status.get("categoryCounts",{});errors=[]
    if status.get("buildMode")!="live": errors.append("quality gate requires a live build")
    if int(status.get("storyCount",0))<MIN_TOTAL: errors.append(f"live story inventory too small: {status.get('storyCount',0)} < {MIN_TOTAL}")
    missing=sorted(cat for cat in REQUIRED_NONEMPTY if int(counts.get(cat,0))<=0)
    if missing: errors.append("empty required categories: "+", ".join(missing))
    collector_errors=status.get("collectorErrors",[]);source_total=73
    if len(collector_errors)/source_total>MAX_ERROR_RATIO: errors.append(f"too many collector failures: {len(collector_errors)}/{source_total}")
    box=json.loads(BOX.read_text(encoding="utf-8"));movies=box.get("movies",[])
    if len(movies)<5: errors.append(f"box office inventory too small: {len(movies)}")
    if errors:
        for error in errors: print("ERROR:",error)
        raise SystemExit(f"V6 live quality gate failed with {len(errors)} error(s).")
    print(f"V6 live quality gate passed: {status['storyCount']} stories, {len(movies)} movies, {len(collector_errors)} collector warnings.")

if __name__=="__main__": main()
