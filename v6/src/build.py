from __future__ import annotations
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from collector import collect_all
from model import Story
from pipeline import process
from registry import load_registry
from specialized import collect_nfl, collect_boxoffice, collect_markets

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/"web";DIST=ROOT/"dist"

def load_fixture(path:Path)->list[Story]:return[Story(**row) for row in json.loads(path.read_text(encoding="utf-8"))]
def write_json(path:Path,payload)->None:path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def build(*,fixture:Path|None=None)->dict:
    registry=load_registry();collector_errors=[]
    if fixture:
        raw=load_fixture(fixture);nfl=[];nfl_error="";boxoffice=[];boxoffice_error="Box Office not used in deterministic fixture build.";markets=[];markets_error="Markets not used in deterministic fixture build."
    else:
        raw,collector_errors=collect_all(registry);nfl,nfl_error=collect_nfl();boxoffice,boxoffice_error=collect_boxoffice();markets,markets_error=collect_markets()
    stories=process(raw,registry);DIST.mkdir(parents=True,exist_ok=True)
    for stale in DIST.iterdir():
        if stale.is_file():stale.unlink()
        elif stale.is_dir():shutil.rmtree(stale)
    for asset in WEB.iterdir():
        if asset.is_file():shutil.copy2(asset,DIST/asset.name)
    by_category={key:[] for key in registry["categories"]}
    for story in stories:by_category.setdefault(story.category,[]).append(story.to_dict())
    generated=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    write_json(DIST/"feed.json",{"version":"6","generatedAt":generated,"categories":registry["categories"],"stories":by_category})
    write_json(DIST/"nfl.json",{"generatedAt":generated,"games":nfl,"error":nfl_error})
    write_json(DIST/"boxoffice.json",{"generatedAt":generated,"localCity":"Farmington, NM","movies":boxoffice,"error":boxoffice_error})
    write_json(DIST/"markets.json",{"generatedAt":generated,"markets":markets,"error":markets_error})
    status={"version":"6","generatedAt":generated,"storyCount":len(stories),"categoryCounts":{k:len(v) for k,v in by_category.items()},"collectorErrors":collector_errors,"nflError":nfl_error,"boxOfficeError":boxoffice_error,"marketsError":markets_error,"buildMode":"fixture" if fixture else "live"}
    write_json(DIST/"status.json",status);return status

def main()->None:
    parser=argparse.ArgumentParser();parser.add_argument("--fixture",type=Path);args=parser.parse_args();print(json.dumps(build(fixture=args.fixture),indent=2))
if __name__=="__main__":main()
