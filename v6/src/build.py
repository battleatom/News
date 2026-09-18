from __future__ import annotations
import argparse
import json
import shutil
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from collector import collect_all
from feedback import apply_pools, fetch_pools, REASONS
from markets import ALPHA_VANTAGE_API_KEY, collect_markets
from model import Story
from movie_artwork import ensure_movie_artwork
from pipeline import process
from pool_policy import apply_rolling_pool
from registry import load_registry
from nfl import collect_nfl
from specialized import collect_boxoffice
from xslots import select_fixed_x_slots

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/"web";DIST=ROOT/"dist"
DATA_FILES=("feed.json","nfl.json","boxoffice.json","markets.json","status.json")
COMING_SOON_SVG='''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="750" viewBox="0 0 500 750"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0c1832"/><stop offset="1" stop-color="#25365e"/></linearGradient></defs><rect width="500" height="750" fill="url(#g)"/><rect x="42" y="42" width="416" height="666" rx="24" fill="none" stroke="#ffffff" stroke-opacity=".22" stroke-width="3"/><text x="250" y="340" text-anchor="middle" fill="#ffffff" font-family="Arial,sans-serif" font-size="34" font-weight="700" letter-spacing="5">COMING</text><text x="250" y="392" text-anchor="middle" fill="#ffffff" font-family="Arial,sans-serif" font-size="34" font-weight="700" letter-spacing="5">SOON</text><text x="250" y="450" text-anchor="middle" fill="#aebbd5" font-family="Arial,sans-serif" font-size="17">OFFICIAL ARTWORK PENDING</text></svg>'''
COMING_SOON_POSTER="data:image/svg+xml;charset=UTF-8,"+urllib.parse.quote(COMING_SOON_SVG,safe="")

def load_fixture(path:Path)->list[Story]:return[Story(**row) for row in json.loads(path.read_text(encoding="utf-8"))]
def write_json(path:Path,payload)->None:path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def prepare_dist(*,data_only:bool)->None:
    DIST.mkdir(parents=True,exist_ok=True)
    if data_only:
        for name in DATA_FILES:
            target=DIST/name
            if target.exists():target.unlink()
        return
    for stale in DIST.iterdir():
        if stale.is_file():stale.unlink()
        elif stale.is_dir():shutil.rmtree(stale)
    for asset in WEB.iterdir():
        if asset.is_file():shutil.copy2(asset,DIST/asset.name)

def apply_upcoming_placeholders(movies:list[dict],artwork_status:dict)->dict:
    placeholder_count=0
    for movie in movies:
        if movie.get("status")=="upcoming" and not movie.get("poster"):
            movie["poster"]=COMING_SOON_POSTER;movie["posterReachable"]=True;movie["artworkSource"]="Coming Soon placeholder";movie["posterPlaceholder"]=True;placeholder_count+=1
        else:movie["posterPlaceholder"]=False
    total=len(movies);reachable=sum(bool(movie.get("poster")) and movie.get("posterReachable") is True for movie in movies)
    artwork_status=dict(artwork_status);artwork_status.update({"movieCount":total,"posterCount":reachable,"reachablePosterCount":reachable,"missingPosterCount":max(0,total-reachable),"posterCoverage":round(reachable/total,4) if total else 0.0,"comingSoonPlaceholderCount":placeholder_count})
    return artwork_status

def build(*,fixture:Path|None=None,data_only:bool=False)->dict:
    registry=load_registry();collector_errors=[];pools={reason:[] for reason in REASONS};feedback_removed={reason:0 for reason in REASONS}
    if fixture:
        raw=load_fixture(fixture);collected_raw=list(raw);nfl=[];nfl_error="";boxoffice=[];boxoffice_error="Box Office not used in deterministic fixture build.";markets=[];markets_error="Markets not used in deterministic fixture build.";artwork_status={"movieCount":0,"posterCount":0,"missingPosterCount":0,"posterCoverage":0.0,"fallbackFilled":0,"tmdbFallbackFilled":0,"wikipediaFallbackFilled":0,"tmdbConfigured":False,"comingSoonPlaceholderCount":0}
    else:
        def timed(label, fn):
            print(f"[v6] START {label}", flush=True);started=time.monotonic()
            result=fn()
            print(f"[v6] DONE {label} {time.monotonic()-started:.1f}s", flush=True)
            return result
        raw,collector_errors=timed("news collectors",lambda:collect_all(registry));collected_raw=list(raw)
        nfl,nfl_error=timed("NFL",collect_nfl)
        boxoffice,boxoffice_error=timed("box office",collect_boxoffice)
        artwork_status=timed("movie artwork",lambda:ensure_movie_artwork(boxoffice));artwork_status=apply_upcoming_placeholders(boxoffice,artwork_status)
        markets,markets_error=timed("markets",collect_markets)
        try:pools=timed("feedback pools",fetch_pools)
        except Exception as exc:
            print(f"[v6] WARN feedback pools: {type(exc).__name__}: {exc}",flush=True);pools={reason:[] for reason in REASONS}
        raw,feedback_removed=apply_pools(raw,pools)
    stories=process(raw,registry)
    if not fixture:stories=select_fixed_x_slots(stories,raw,registry)
    stories,pool_policy=apply_rolling_pool(stories,registry)
    prepare_dist(data_only=data_only)
    full_by_category={key:[] for key in registry["categories"]}
    for story in stories:full_by_category.setdefault(story.category,[]).append(story.to_dict())
    by_category={};reserves={};visible_counts={};reserve_counts={}
    for key,cfg in registry["categories"].items():
        rows=full_by_category.get(key,[]);visible_target=int(cfg.get("visible_target",cfg.get("target",50)))
        visible=rows[:visible_target];reserve=rows[visible_target:]
        by_category[key]=visible;reserves[key]=reserve;visible_counts[key]=len(visible);reserve_counts[key]=len(reserve)
    generated=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    market_sources=sorted({str(row.get("source") or "") for row in markets if row.get("source")})
    alpha_used=sum(1 for row in markets if row.get("source")=="Alpha Vantage")
    market_status={"alphaVantageConfigured":bool(ALPHA_VANTAGE_API_KEY) if not fixture else False,"alphaVantageUsed":alpha_used,"sources":market_sources,"instrumentCount":len(markets)}
    write_json(DIST/"feed.json",{"version":"6","generatedAt":generated,"categories":registry["categories"],"stories":by_category,"reserves":reserves,"poolPolicy":pool_policy})
    write_json(DIST/"nfl.json",{"generatedAt":generated,"games":nfl,"error":nfl_error})
    write_json(DIST/"boxoffice.json",{"generatedAt":generated,"localCity":"Farmington, NM","movies":boxoffice,"artwork":artwork_status,"error":boxoffice_error})
    write_json(DIST/"markets.json",{"generatedAt":generated,"markets":markets,"providerStatus":market_status,"error":markets_error})
    error_by_source={row.get("source",""):row.get("error","") for row in collector_errors}
    raw_counts={}
    for story in collected_raw:
        sid=str(getattr(story,"source_id","") or "")
        if sid:raw_counts[sid]=raw_counts.get(sid,0)+1
    source_statuses=[] if fixture else [{"id":row.get("id",""),"name":row.get("name",row.get("id","")),"category":row.get("category",""),"status":"error" if row.get("id","") in error_by_source else ("degraded" if raw_counts.get(row.get("id",""),0)==0 else "live"),"storyCount":raw_counts.get(row.get("id",""),0),"error":error_by_source.get(row.get("id","") ,"")} for row in registry.get("sources",[])]
    healthy_sources=sum(1 for row in source_statuses if row["status"]=="live")
    pool_total=sum(visible_counts.values())+sum(reserve_counts.values())
    status={"version":"6","generatedAt":generated,"storyCount":pool_total,"visibleStoryCount":sum(visible_counts.values()),"poolStoryCount":pool_total,"categoryCounts":visible_counts,"reserveCounts":reserve_counts,"reserveStoryCount":sum(reserve_counts.values()),"poolPolicy":pool_policy,"collectorErrors":collector_errors,"sourceStatuses":source_statuses,"sourceCount":len(source_statuses),"healthySourceCount":healthy_sources,"feedbackEnforcement":"server","feedbackPoolCounts":{reason:len(pools.get(reason,[])) for reason in REASONS},"feedbackRemovedCount":sum(feedback_removed.values()),"feedbackRemovedByReason":feedback_removed,"nflError":nfl_error,"boxOfficeError":boxoffice_error,"boxOfficeArtwork":artwork_status,"marketsError":markets_error,"marketData":market_status,"buildMode":"fixture" if fixture else "live","applicationAssetsWritten":not data_only}
    write_json(DIST/"status.json",status);return status

def main()->None:
    parser=argparse.ArgumentParser();parser.add_argument("--fixture",type=Path);parser.add_argument("--data-only",action="store_true",help="Refresh only dynamic JSON; never rewrite V6 application assets.");args=parser.parse_args();print(json.dumps(build(fixture=args.fixture,data_only=args.data_only),indent=2))
if __name__=="__main__":main()
