from __future__ import annotations
import json
import re
import urllib.parse
import urllib.request

from model import Story

API_URL="https://bkcrgfkhgjypvzwubwrh.supabase.co/functions/v1/news-feedback"
REASONS=("D","NR","NW")
TIMEOUT=15


def _text(value:str|None)->str:
    return re.sub(r"\s+"," ",(value or "").lower()).strip()


def _url(value:str|None)->str:
    raw=(value or "").strip()
    if not raw:return ""
    try:
        parts=urllib.parse.urlsplit(raw)
        if parts.scheme not in {"http","https"}:return ""
        drop={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid"}
        query=urllib.parse.urlencode([(k,v) for k,v in urllib.parse.parse_qsl(parts.query,keep_blank_values=True) if k.lower() not in drop])
        return urllib.parse.urlunsplit((parts.scheme.lower(),parts.netloc.lower(),parts.path,query,"")).rstrip("/").lower()
    except Exception:
        return raw.rstrip("/").lower()


def fetch_pools()->dict[str,list[dict]]:
    request=urllib.request.Request(API_URL,headers={"Accept":"application/json","User-Agent":"Underreported-V6/1.0"})
    with urllib.request.urlopen(request,timeout=TIMEOUT) as response:
        if response.status!=200:raise RuntimeError(f"feedback API returned HTTP {response.status}")
        payload=json.loads(response.read().decode("utf-8"))
    raw=payload.get("pools") if isinstance(payload,dict) else None
    if not isinstance(raw,dict):raise RuntimeError("feedback API payload has no pools object")
    pools={reason:[] for reason in REASONS}
    for reason in REASONS:
        rows=raw.get(reason,[])
        if not isinstance(rows,list):raise RuntimeError(f"feedback pool {reason} is not a list")
        pools[reason]=[row for row in rows if isinstance(row,dict)]
    return pools


def _matches(story:Story,record:dict,require_category:bool)->bool:
    if require_category:
        category=_text(record.get("category") or record.get("tab"))
        if category and category!=_text(story.category):return False
    story_url=_url(story.url);record_url=_url(record.get("url_key") or record.get("url"))
    if story_url and record_url and story_url==record_url:return True
    return bool(
        _text(record.get("title_key") or record.get("title"))==_text(story.title)
        and _text(record.get("source_key") or record.get("source"))==_text(story.source)
        and _text(story.title)
    )


def matched_reason(story:Story,pools:dict[str,list[dict]])->str|None:
    if any(_matches(story,row,False) for row in pools.get("D",[])):return "D"
    for reason in ("NR","NW"):
        if any(_matches(story,row,True) for row in pools.get(reason,[])):return reason
    return None


def apply_pools(stories:list[Story],pools:dict[str,list[dict]])->tuple[list[Story],dict[str,int]]:
    kept=[];removed={reason:0 for reason in REASONS}
    for story in stories:
        reason=matched_reason(story,pools)
        if reason:removed[reason]+=1
        else:kept.append(story)
    return kept,removed
