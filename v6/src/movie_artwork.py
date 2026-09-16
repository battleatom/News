from __future__ import annotations

import difflib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA="Mozilla/5.0 Underreported-V6/1.0"
TIMEOUT=15
TMDB_API_KEY=os.environ.get("TMDB_API_KEY","").strip()
TMDB_IMAGE_BASE="https://image.tmdb.org/t/p/w500"
CURRENT_YEAR=datetime.now(timezone.utc).year
SPECIAL_POSTERS={
    "sb19wakasatsimulathetrilogyconcertfinaleincinemas":"https://atom-tickets-res.cloudinary.com/image/upload/v1/ingestion-images-archive-prod/westworld/assets/424547r1.jpg",
}

def _clean(value:str)->str:
    value=html.unescape(value or "")
    value=re.sub(r"<[^>]+>"," ",value)
    return re.sub(r"\s+"," ",value).strip()

def _key(value:str)->str:return re.sub(r"[^a-z0-9]+","",_clean(value).lower().replace("&"," and "))

def _request(url:str,accept:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":accept,"Accept-Language":"en-US,en;q=0.8"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as response:return response.read()

def _json(url:str)->dict:return json.loads(_request(url,"application/json").decode("utf-8","replace"))
def _text(url:str)->str:return _request(url,"text/html,application/xhtml+xml").decode("utf-8","replace")

def _similarity(left:str,right:str)->float:
    a,b=_key(left),_key(right)
    if not a or not b:return 0.0
    if a==b:return 1.0
    return difflib.SequenceMatcher(None,a,b).ratio()

def _normalize_poster_url(url:str)->str:
    url=html.unescape((url or "").strip())
    if not url:return ""
    try:parsed=urllib.parse.urlsplit(url)
    except Exception:return url
    if parsed.netloc.lower()=="media.themoviedb.org":
        match=re.search(r"/t/p/[^/]+/(.+)$",parsed.path)
        if match:return f"{TMDB_IMAGE_BASE}/{match.group(1).lstrip('/')}"
    return url

def _poster_reachable(url:str)->bool:
    url=_normalize_poster_url(url)
    if not url:return False
    try:
        req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8","Range":"bytes=0-2047"})
        with urllib.request.urlopen(req,timeout=TIMEOUT) as response:
            content_type=(response.headers.get("Content-Type") or "").lower();sample=response.read(64)
        if content_type.startswith("image/"):return True
        return sample.startswith((b"\xff\xd8\xff",b"\x89PNG\r\n\x1a\n",b"GIF87a",b"GIF89a",b"RIFF")) or b"<svg" in sample.lower()
    except Exception:return False

def _valid_result(result:dict)->bool:
    poster=_normalize_poster_url(str(result.get("poster") or ""))
    if not poster or not _poster_reachable(poster):return False
    result["poster"]=poster;return True

def _is_schedule_label(title:str)->bool:
    value=_clean(title).lower()
    if not value:return True
    months="january|february|march|april|may|june|july|august|september|october|november|december"
    seasons="spring|summer|fall|autumn|winter"
    return bool(re.fullmatch(rf"(?:{months})\s+20\d{{2}}",value) or re.fullmatch(rf"(?:{seasons})\s+20\d{{2}}",value) or re.fullmatch(r"(?:1st|2nd|3rd|4th)\s+quarter",value) or value in {"time","date","title","movie","movies","release date","release schedule","tbd","to be announced"})

def _title_variants(title:str)->list[str]:
    title=_clean(title);variants=[title]
    no_cinema=re.sub(r"\s+in\s+cinemas\s*$","",title,flags=re.I).strip()
    if no_cinema and no_cinema not in variants:variants.append(no_cinema)
    no_suffix=re.sub(r"\s*[:–—-]\s*(?:the\s+)?(?:trilogy\s+)?concert.*$","",no_cinema,flags=re.I).strip()
    if len(no_suffix)>=4 and no_suffix not in variants:variants.append(no_suffix)
    if ":" in title:
        short=title.split(":",1)[0].strip()
        if len(short)>=4 and short not in variants:variants.append(short)
    return variants

def _special(title:str)->dict:
    poster=SPECIAL_POSTERS.get(_key(title),"")
    return {"poster":poster,"metadataSource":"Atom Tickets","artworkSource":"Atom Tickets"} if poster else {}

def _tmdb(title:str,release_date:str="")->dict:
    if not TMDB_API_KEY:return {}
    target_year=(release_date or "")[:4];attempts=([target_year] if target_year.isdigit() else [])+[""];best=None;best_score=0.0
    for year in attempts:
        try:
            params={"api_key":TMDB_API_KEY,"query":title,"include_adult":"false","language":"en-US"}
            if year:params["year"]=year
            payload=_json("https://api.themoviedb.org/3/search/movie?"+urllib.parse.urlencode(params))
            for item in payload.get("results") or []:
                candidate=item.get("title") or item.get("original_title") or "";score=_similarity(title,candidate);item_year=str(item.get("release_date") or "")[:4]
                if target_year and item_year==target_year:score+=.08
                elif target_year and item_year and item_year!=target_year:score-=.06
                if item.get("poster_path"):score+=.03
                if score>best_score:best_score,best=score,item
        except Exception:continue
    if not best or best_score<.82:return {}
    poster=best.get("poster_path") or ""
    return {"poster":TMDB_IMAGE_BASE+poster if poster else "","overview":_clean(best.get("overview") or ""),"voteAverage":best.get("vote_average") or 0,"tmdbId":best.get("id") or "","metadataSource":"TMDB","artworkSource":"TMDB" if poster else ""}

def _meta(page:str,key:str)->str:
    for pattern in (rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(key)}["\']',rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']'):
        match=re.search(pattern,page,re.I|re.S)
        if match:return html.unescape(match.group(1)).strip()
    return ""

def _tmdb_web(title:str,release_date:str="")->dict:
    try:page=_text("https://www.themoviedb.org/search/movie?"+urllib.parse.urlencode({"query":title,"language":"en-US"}))
    except Exception:return {}
    paths=[]
    for match in re.finditer(r'href=["\'](/movie/\d+[^"\']*)["\']',page,re.I):
        path=html.unescape(match.group(1)).split("?")[0]
        if path not in paths:paths.append(path)
        if len(paths)>=8:break
    target_year=(release_date or "")[:4];best={};best_score=0.0
    for path in paths:
        try:detail=_text(urllib.parse.urljoin("https://www.themoviedb.org",path))
        except Exception:continue
        page_title=_meta(detail,"og:title") or _clean((re.search(r"<title[^>]*>(.*?)</title>",detail,re.I|re.S) or ["",""])[1]);page_title=re.sub(r"\s*[—|-]\s*The Movie Database.*$","",page_title,flags=re.I).strip();score=_similarity(title,re.sub(r"\s*\(\d{4}\)\s*$","",page_title))
        if target_year and target_year in detail:score+=.06
        poster=_normalize_poster_url(_meta(detail,"og:image") or _meta(detail,"twitter:image"))
        if poster:score+=.03
        if score>best_score and poster:
            mid=re.search(r"/movie/(\d+)",path);best_score=score;best={"poster":poster,"overview":_meta(detail,"og:description"),"tmdbId":mid.group(1) if mid else "","metadataSource":"TMDB Web","artworkSource":"TMDB Web"}
    return best if best_score>=.78 else {}

def _showtimes_artwork(movie_url:str)->dict:
    if not movie_url or "showtimes.com" not in movie_url:return {}
    try:page=_text(movie_url)
    except Exception:return {}
    poster=_meta(page,"og:image") or _meta(page,"twitter:image")
    if not poster:
        images=re.findall(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\'][^>]*>',page,re.I|re.S);poster=next((html.unescape(url) for url in images if any(token in url.lower() for token in ("poster","movie","film"))),"")
    return {"poster":urllib.parse.urljoin(movie_url,poster),"overview":_meta(page,"og:description"),"metadataSource":"Showtimes.com","artworkSource":"Showtimes.com"} if poster else {}

def _wiki_summary(page_title:str)->dict:
    try:payload=_json("https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(page_title.replace(" ","_")))
    except Exception:return {}
    extract=_clean(payload.get("extract") or "");description=_clean(payload.get("description") or "");text=f" {description.lower()} {extract[:400].lower()} "
    if not any(token in text for token in (" film "," movie "," motion picture "," directed by "," starring "," documentary "," animated ")):return {}
    poster=((payload.get("thumbnail") or {}).get("source") or "").strip()
    return {"poster":poster,"overview":extract,"metadataSource":"Wikipedia","artworkSource":"Wikipedia" if poster else "","wikiTitle":payload.get("title") or page_title}

def _wikipedia(title:str,release_date:str="")->dict:
    year=(release_date or "")[:4];year=year if year.isdigit() else str(CURRENT_YEAR)
    for page_title in (f"{title} ({year} film)",f"{title} (film)",title):
        result=_wiki_summary(page_title)
        if result.get("poster"):return result
    try:payload=_json("https://en.wikipedia.org/w/api.php?"+urllib.parse.urlencode({"action":"query","list":"search","srsearch":f'"{title}" film {year}',"srlimit":"8","format":"json","utf8":"1","origin":"*"}))
    except Exception:return {}
    candidates=[]
    for row in (payload.get("query") or {}).get("search") or []:
        page_title=_clean(row.get("title") or "")
        if not page_title:continue
        score=_similarity(title,re.sub(r"\s*\([^)]*\)\s*$","",page_title))+(0.08 if year in page_title else 0)+(0.05 if "film" in page_title.lower() else 0);candidates.append((score,page_title))
    for _,page_title in sorted(candidates,reverse=True):
        result=_wiki_summary(page_title)
        if result.get("poster"):return result
    return {}

def _find_artwork(title:str,release_date:str,movie_url:str)->dict:
    variants=_title_variants(title)
    for candidate in variants:
        result=_tmdb(candidate,release_date)
        if _valid_result(result):return result
    for candidate in variants:
        result=_tmdb_web(candidate,release_date)
        if _valid_result(result):return result
    result=_showtimes_artwork(movie_url)
    if _valid_result(result):return result
    result=_special(title)
    if _valid_result(result):return result
    for candidate in variants:
        result=_wikipedia(candidate,release_date)
        if _valid_result(result):return result
    return {}

def ensure_movie_artwork(movies:list[dict])->dict:
    movies[:]=[movie for movie in movies if not _is_schedule_label(str(movie.get("title") or ""))];total=len(movies);filled=0;repaired=0;source_fills={}
    for movie in movies:
        original=_normalize_poster_url(str(movie.get("poster") or ""))
        if original and _poster_reachable(original):
            movie["poster"]=original;movie["posterReachable"]=True;movie.setdefault("artworkSource",movie.get("metadataSource") or "existing");continue
        if original:repaired+=1
        movie["poster"]="";movie["posterReachable"]=False;title=str(movie.get("title") or "").strip()
        if not title:continue
        result=_find_artwork(title,str(movie.get("releaseDate") or ""),str(movie.get("movieUrl") or ""))
        if not result:continue
        movie["poster"]=result["poster"];movie["posterReachable"]=True
        if not movie.get("overview") and result.get("overview"):movie["overview"]=result["overview"]
        if not movie.get("tmdbId") and result.get("tmdbId"):movie["tmdbId"]=result["tmdbId"]
        if not movie.get("voteAverage") and result.get("voteAverage"):movie["voteAverage"]=result["voteAverage"]
        if result.get("metadataSource"):movie["metadataSource"]=result["metadataSource"]
        movie["artworkSource"]=result.get("artworkSource") or result.get("metadataSource") or "fallback";filled+=1;source_fills[movie["artworkSource"]]=source_fills.get(movie["artworkSource"],0)+1
    reachable=sum(bool(movie.get("poster")) and movie.get("posterReachable") is True for movie in movies)
    return {"movieCount":total,"posterCount":reachable,"reachablePosterCount":reachable,"missingPosterCount":max(0,total-reachable),"posterCoverage":round(reachable/total,4) if total else 0.0,"fallbackFilled":filled,"repairedBrokenPosters":repaired,"fallbackFilledBySource":source_fills,"tmdbConfigured":bool(TMDB_API_KEY)}
