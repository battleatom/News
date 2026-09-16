from __future__ import annotations
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from collector import collect_all
from feedback import apply_pools, fetch_pools, REASONS
from model import Story
from pipeline import process
from registry import load_registry
from nfl import collect_nfl
from specialized import collect_boxoffice, collect_markets
from xslots import select_fixed_x_slots

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/"web";DIST=ROOT/"dist"

def load_fixture(path:Path)->list[Story]:return[Story(**row) for row in json.loads(path.read_text(encoding="utf-8"))]
def write_json(path:Path,payload)->None:path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def build(*,fixture:Path|None=None)->dict:
    registry=load_registry();collector_errors=[];pools={reason:[] for reason in REASONS};feedback_removed={reason:0 for reason in REASONS}
    if fixture:
        raw=load_fixture(fixture);collected_raw=list(raw);nfl=[];nfl_error="";boxoffice=[];boxoffice_error="Box Office not used in deterministic fixture build.";markets=[];markets_error="Markets not used in deterministic fixture build."
    else:
        raw,collector_errors=collect_all(registry);collected_raw=list(raw);nfl,nfl_error=collect_nfl();boxoffice,boxoffice_error=collect_boxoffice();markets,markets_error=collect_markets();pools=fetch_pools();raw,feedback_removed=apply_pools(raw,pools)
    stories=process(raw,registry)
    if not fixture:stories=select_fixed_x_slots(stories,raw,registry)
    DIST.mkdir(parents=True,exist_ok=True)
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
    error_by_source={row.get("source",""):row.get("error","") for row in collector_errors}
    raw_counts={}
    for story in collected_raw:
        sid=str(getattr(story,"source_id","") or "")
        if sid:raw_counts[sid]=raw_counts.get(sid,0)+1
    source_statuses=[] if fixture else [{"id":row.get("id",""),"name":row.get("name",row.get("id","")),"category":row.get("category",""),"status":"error" if row.get("id","") in error_by_source else "live","storyCount":raw_counts.get(row.get("id",""),0),"error":error_by_source.get(row.get("id",""),"")} for row in registry.get("sources",[])]
    healthy_sources=sum(1 for row in source_statuses if row["status"]=="live")
    status={"version":"6","generatedAt":generated,"storyCount":len(stories),"categoryCounts":{k:len(v) for k,v in by_category.items()},"collectorErrors":collector_errors,"sourceStatuses":source_statuses,"sourceCount":len(source_statuses),"healthySourceCount":healthy_sources,"feedbackEnforcement":"server","feedbackPoolCounts":{reason:len(pools.get(reason,[])) for reason in REASONS},"feedbackRemovedCount":sum(feedback_removed.values()),"feedbackRemovedByReason":feedback_removed,"nflError":nfl_error,"boxOfficeError":boxoffice_error,"marketsError":markets_error,"buildMode":"fixture" if fixture else "live"}
    write_json(DIST/"status.json",status);return status

def main()->None:
    parser=argparse.ArgumentParser();parser.add_argument("--fixture",type=Path);args=parser.parse_args();print(json.dumps(build(fixture=args.fixture),indent=2))
if __name__=="__main__":main()
