from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];STATUS=ROOT/"dist"/"status.json";BOX=ROOT/"dist"/"boxoffice.json";MARKETS=ROOT/"dist"/"markets.json"
REQUIRED_NONEMPTY={"top","nfl","underreported","world","us","presidential","federal","legislation","nm","local","region","technology","gaming","military","entertainment"};MIN_TOTAL=120;MAX_ERROR_RATIO=0.35;MIN_POSTER_COVERAGE=0.80

def main()->None:
    status=json.loads(STATUS.read_text(encoding="utf-8"));counts=status.get("categoryCounts",{});errors=[]
    if status.get("buildMode")!="live":errors.append("quality gate requires a live build")
    if int(status.get("storyCount",0))<MIN_TOTAL:errors.append(f"live story inventory too small: {status.get('storyCount',0)} < {MIN_TOTAL}")
    missing=sorted(cat for cat in REQUIRED_NONEMPTY if int(counts.get(cat,0))<=0)
    if missing:errors.append("empty required categories: "+", ".join(missing))
    collector_errors=status.get("collectorErrors",[]);source_total=max(1,int(status.get("sourceCount",0) or 1))
    if len(collector_errors)/source_total>MAX_ERROR_RATIO:errors.append(f"too many collector failures: {len(collector_errors)}/{source_total}")
    box=json.loads(BOX.read_text(encoding="utf-8"));movies=box.get("movies",[]);playing=[m for m in movies if m.get("status")!="upcoming"]
    if len(movies)<5:errors.append(f"box office inventory too small: {len(movies)}")
    if playing and not any(m.get("theaters") for m in playing):errors.append("box office has no local theater/showtime payloads")
    if any("leavingSoon" not in m for m in movies):errors.append("box office leaving-soon schema missing")
    poster_count=sum(bool(m.get("poster")) for m in movies);poster_coverage=(poster_count/len(movies)) if movies else 0.0
    if movies and poster_coverage<MIN_POSTER_COVERAGE:errors.append(f"box office poster coverage too low: {poster_count}/{len(movies)} ({poster_coverage:.0%}) < {MIN_POSTER_COVERAGE:.0%}")
    markets=json.loads(MARKETS.read_text(encoding="utf-8")).get("markets",[])
    if len(markets)<4:errors.append(f"market inventory too small: {len(markets)}")
    if errors:
        for error in errors:print("ERROR:",error)
        raise SystemExit(f"V6 live quality gate failed with {len(errors)} error(s).")
    print(f"V6 live quality gate passed: {status['storyCount']} stories, {len(movies)} movies, {poster_count}/{len(movies)} posters ({poster_coverage:.0%}), {sum(bool(m.get('theaters')) for m in movies)} local-showtime movies, {len(markets)} markets, {len(collector_errors)} collector warnings.")
if __name__=="__main__":main()
