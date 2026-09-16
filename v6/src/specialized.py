from __future__ import annotations
import difflib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

UA="Mozilla/5.0 Underreported-V6/1.0"
TIMEOUT=18

def fetch_json(url:str)->dict:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as response:return json.load(response)

def fetch_text(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/rss+xml"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as response:return response.read().decode("utf-8","replace")

def clean(value:str)->str:
    value=html.unescape(value or "");value=re.sub(r"<[^>]+>"," ",value);return re.sub(r"\s+"," ",value).strip()

def title_key(value:str)->str:return re.sub(r"[^a-z0-9]+","",clean(value).lower().replace("&"," and "))

def collect_nfl()->tuple[list[dict],str]:
    try:
        payload=fetch_json("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard");rows=[]
        for event in payload.get("events",[]):
            competition=(event.get("competitions") or [{}])[0];teams=[]
            for comp in competition.get("competitors") or []:
                team=comp.get("team") or {};teams.append({"name":team.get("displayName") or team.get("shortDisplayName") or "","abbr":team.get("abbreviation") or "","score":comp.get("score") or "","homeAway":comp.get("homeAway") or "","logo":team.get("logo") or "","color":team.get("color") or ""})
            state=((event.get("status") or {}).get("type") or {}).get("state") or "";plays=[]
            if state=="in":
                try:
                    summary=fetch_json("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event="+urllib.parse.quote(str(event.get("id") or "")))
                    for play in (summary.get("plays") or [])[-10:]:
                        clock=(play.get("clock") or {}).get("displayValue") or "";period=(play.get("period") or {}).get("number") or "";text=play.get("text") or ""
                        if text:plays.append({"clock":clock,"period":period,"text":text})
                except Exception:pass
            rows.append({"id":event.get("id") or "","name":event.get("name") or "","shortName":event.get("shortName") or "","date":event.get("date") or "","status":((event.get("status") or {}).get("type") or {}).get("description") or "","detail":((event.get("status") or {}).get("type") or {}).get("detail") or "","state":state,"teams":teams,"broadcasts":[name for group in competition.get("broadcasts",[]) for name in group.get("names",[])],"venue":((competition.get("venue") or {}).get("fullName") or ""),"plays":plays})
        return rows,""
    except Exception as exc:return [],f"{type(exc).__name__}: {exc}"

MARKETS=[("^GSPC","S&P 500"),("^DJI","DOW"),("^IXIC","NASDAQ"),("^RUT","RUSSELL 2000"),("^VIX","VIX"),("CL=F","WTI OIL"),("BZ=F","BRENT"),("NG=F","NAT GAS"),("GC=F","GOLD"),("SI=F","SILVER"),("HG=F","COPPER"),("DX-Y.NYB","U.S. DOLLAR"),("^TNX","10Y"),("BTC-USD","BITCOIN"),("ETH-USD","ETHEREUM")]
def collect_markets()->tuple[list[dict],str]:
    rows=[];errors=[]
    for symbol,label in MARKETS:
        try:
            url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol,safe="")+"?range=5d&interval=1d";result=((fetch_json(url).get("chart") or {}).get("result") or [{}])[0];meta=result.get("meta") or {};price=meta.get("regularMarketPrice");prev=meta.get("chartPreviousClose") or meta.get("previousClose") or meta.get("regularMarketPreviousClose")
            if price is None:
                closes=(((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []);valid=[x for x in closes if isinstance(x,(int,float))]
                if valid:price=valid[-1];prev=valid[-2] if len(valid)>1 else prev
            if price is None:continue
            change=((float(price)-float(prev))/float(prev)*100) if prev else 0;rows.append({"symbol":symbol,"label":label,"price":round(float(price),2),"previousClose":round(float(prev),2) if prev else None,"changePct":change,"currency":meta.get("currency") or "USD","marketState":meta.get("marketState") or ""})
        except Exception as exc:errors.append(f"{symbol}: {type(exc).__name__}")
    return rows,"; ".join(errors)

SHOWTIMES_SLUG=os.environ.get("BOXOFFICE_CITY_SLUG","farmington-nm").strip() or "farmington-nm"
SHOWTIMES_LABEL=os.environ.get("BOXOFFICE_CITY_LABEL","Farmington, NM").strip() or "Farmington, NM"
SHOWTIMES_URL=f"https://www.showtimes.com/movie-times/{SHOWTIMES_SLUG}/"
RELEASE_YEAR=datetime.now(timezone.utc).year
RELEASE_URL=f"https://www.the-numbers.com/movies/release-schedule/{RELEASE_YEAR}"
TMDB_API_KEY=os.environ.get("TMDB_API_KEY","").strip()
TMDB_IMAGE_BASE="https://image.tmdb.org/t/p/w500"

def parse_local_showtimes(page:str)->list[dict]:
    blocks=list(re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2[^>]*>|</main>|</body>)",page,re.I|re.S));current="";rows=[]
    for match in blocks:
        heading_html=match.group(1);heading=clean(heading_html);body=clean(match.group(2))
        if heading.lower().startswith(("allen theatres","amc ","regal ","cinemark ","harkins ")):current=heading;continue
        times=re.findall(r"\b(?:[1-9]|1[0-2]):[0-5]\d\s*(?:am|pm)\b",body,re.I)
        if not current or not heading or not times:continue
        rating=(re.search(r"\b(G|PG|PG-13|R|NC-17|NR)\b",body) or [None,""])[1];runtime=(re.search(r"\b(\d+h\s*\d+m|\d+h|\d+m)\b",body) or [None,""])[1];href=re.search(r'href=["\']([^"\']+)["\']',heading_html,re.I)
        rows.append({"title":heading.replace(" Watch Trailer","").strip(),"theater":current,"rating":rating,"runtime":runtime,"showtimes":list(dict.fromkeys(times)),"movieUrl":urllib.parse.urljoin(SHOWTIMES_URL,html.unescape(href.group(1))) if href else ""})
    return rows

def parse_release_schedule(page:str)->list[dict]:
    month_re=r"(?:January|February|March|April|May|June|July|August|September|October|November|December)";out=[];seen=set();current_month="";last_date:date|None=None
    tokens=re.split(r"(<h[1-3][^>]*>.*?</h[1-3]>|<tr[^>]*>.*?</tr>)",page,flags=re.I|re.S)
    for token in tokens:
        heading=re.match(r"<h[1-3][^>]*>(.*?)</h[1-3]>",token,re.I|re.S)
        if heading:
            m=re.search(fr"\b({month_re})\s+{RELEASE_YEAR}\b",clean(heading.group(1)),re.I)
            if m:current_month=m.group(1).title()
            continue
        if not token.lower().startswith("<tr"):continue
        cells=[clean(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>",token,re.I|re.S)]
        if not cells:continue
        first=cells[0];title_idx=1
        dm=re.search(fr"\b({month_re})\s+(\d{{1,2}})(?:,?\s+({RELEASE_YEAR}))?\b",first,re.I)
        if dm:
            try:last_date=datetime.strptime(f"{dm.group(1)} {dm.group(2)} {RELEASE_YEAR}","%B %d %Y").date()
            except ValueError:last_date=None
        elif re.fullmatch(r"\d{1,2}",first) and current_month:
            try:last_date=datetime.strptime(f"{current_month} {int(first)} {RELEASE_YEAR}","%B %d %Y").date()
            except ValueError:last_date=None
        elif last_date is not None and first:title_idx=0
        else:continue
        if last_date is None or title_idx>=len(cells):continue
        title=re.sub(r"\s*\([^)]*(?:Wide|Limited|IMAX|re-release|Special Engagement|Event)[^)]*\)\s*$","",cells[title_idx],flags=re.I).strip();key=(title_key(title),last_date.isoformat())
        if not key[0] or key in seen:continue
        seen.add(key);out.append({"title":title,"releaseDate":last_date.isoformat()})
    return out

def parse_availability_dates(page:str)->list[date]:
    today=datetime.now(timezone.utc).date();found=set()
    for y,m,d in re.findall(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",page):
        try:found.add(date(int(y),int(m),int(d)))
        except ValueError:pass
    for m,d,y in re.findall(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b",clean(page)):
        try:found.add(date(int(y),int(m),int(d)))
        except ValueError:pass
    months=r"January|February|March|April|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr"
    for mon,day_num,year in re.findall(fr"\b({months})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b",clean(page),re.I):
        try:found.add(datetime.strptime(f"{mon} {day_num} {year}","%b %d %Y" if len(mon)<=3 else "%B %d %Y").date())
        except ValueError:pass
    return sorted(d for d in found if d>=today)

def google_movie_news(title:str)->list[dict]:
    try:
        q=urllib.parse.quote(f'"{title}" movie when:30d');root=ET.fromstring(fetch_text(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"));rows=[]
        for item in root.findall(".//item")[:3]:
            t=clean(item.findtext("title"));link=clean(item.findtext("link"));source=clean(item.findtext("source"));pub=clean(item.findtext("pubDate"))
            if t and link:rows.append({"title":t,"link":link,"source":source,"pubDate":pub})
        return rows
    except Exception:return []

def tmdb_movie(title:str,release_date:str="")->dict:
    if not TMDB_API_KEY:return{}
    try:
        params={"api_key":TMDB_API_KEY,"query":title,"include_adult":"false","language":"en-US"}
        year=(release_date or "")[:4]
        if year.isdigit():params["year"]=year
        payload=fetch_json("https://api.themoviedb.org/3/search/movie?"+urllib.parse.urlencode(params));target=title_key(title);candidates=[]
        for item in payload.get("results") or []:
            found=title_key(item.get("title") or item.get("original_title") or "")
            if not found:continue
            score=1.0 if found==target else difflib.SequenceMatcher(None,target,found).ratio()
            item_year=str(item.get("release_date") or "")[:4]
            year_bonus=.05 if year and item_year==year else 0
            candidates.append((score+year_bonus,item))
        if not candidates:return{}
        score,item=max(candidates,key=lambda pair:pair[0])
        if score<.88:return{}
        poster=item.get("poster_path") or "";overview=clean(item.get("overview") or "")
        return{"overview":overview,"poster":TMDB_IMAGE_BASE+poster if poster else "","voteAverage":item.get("vote_average") or 0,"tmdbId":item.get("id") or "","metadataSource":"TMDB"}
    except Exception:return{}

def wiki_movie(title:str)->dict:
    for candidate in (f"{title} (film)",f"{title} ({RELEASE_YEAR} film)",title):
        try:
            d=fetch_json("https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(candidate.replace(" ","_")));extract=clean(d.get("extract") or "");desc=clean(d.get("description") or "").lower()
            if extract and any(k in f" {desc} {extract[:250].lower()} " for k in (" film "," movie "," motion picture "," directed by "," starring "," documentary "," animated ")):return{"overview":extract,"poster":((d.get("thumbnail") or {}).get("source") or ""),"metadataSource":"Wikipedia"}
        except Exception:continue
    return{"overview":"","poster":""}

def enrich_movie(movie:dict)->dict:
    primary=tmdb_movie(movie["title"],movie.get("releaseDate","") or "")
    fallback={}
    if not primary.get("overview") or not primary.get("poster"):fallback=wiki_movie(movie["title"])
    merged={"overview":primary.get("overview") or fallback.get("overview") or "","poster":primary.get("poster") or fallback.get("poster") or "","voteAverage":primary.get("voteAverage") or movie.get("voteAverage") or 0,"tmdbId":primary.get("tmdbId") or "","metadataSource":primary.get("metadataSource") or fallback.get("metadataSource") or ""}
    movie.update(merged);movie["news"]=google_movie_news(movie["title"]);return movie

def collect_boxoffice()->tuple[list[dict],str]:
    errors=[];local={};today=datetime.now(timezone.utc).date()
    try:local_rows=parse_local_showtimes(fetch_text(SHOWTIMES_URL))
    except Exception as exc:errors.append(f"showtimes: {type(exc).__name__}: {exc}");local_rows=[]
    for row in local_rows:
        movie=local.setdefault(row["title"],{"title":row["title"],"rating":row.get("rating","") ,"runtime":row.get("runtime","") ,"movieUrl":row.get("movieUrl","") ,"theaters":[]})
        if not movie.get("movieUrl") and row.get("movieUrl"):movie["movieUrl"]=row["movieUrl"]
        movie["theaters"].append({"name":row["theater"],"showtimes":row["showtimes"]})
    try:releases=parse_release_schedule(fetch_text(RELEASE_URL))
    except Exception as exc:errors.append(f"releases: {type(exc).__name__}: {exc}");releases=[]
    release_by_key={title_key(r["title"]):r["releaseDate"] for r in releases if title_key(r.get("title",""))};release_keys=list(release_by_key)
    def release_for(title:str)->str:
        key=title_key(title)
        if key in release_by_key:return release_by_key[key]
        matches=difflib.get_close_matches(key,release_keys,n=1,cutoff=.90);return release_by_key.get(matches[0],"") if matches else ""
    availability={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(fetch_text,movie["movieUrl"]):title for title,movie in local.items() if movie.get("movieUrl")}
        for future in as_completed(futures):
            title=futures[future]
            try:availability[title]=parse_availability_dates(future.result())
            except Exception:availability[title]=[]
    confirmed_last={title:max(days) for title,days in availability.items() if days};global_horizon=max(confirmed_last.values()) if confirmed_last else None
    rows=[]
    for title,movie in local.items():
        last=confirmed_last.get(title);leaving=bool(last and global_horizon and last<global_horizon and 0<=(last-today).days<=7)
        rows.append({"id":"local-"+re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")[:70],"title":title,"releaseDate":release_for(title),"overview":"","poster":"","status":"playing","voteAverage":0,"rating":movie.get("rating","") ,"runtime":movie.get("runtime","") ,"theaters":movie["theaters"],"news":[],"source":"Showtimes.com","confirmedThrough":last.isoformat() if last else "","leavingDate":last.isoformat() if leaving and last else "","leavingSoon":leaving})
    local_keys={title_key(title) for title in local}
    upcoming=[]
    for release in releases:
        try:release_date=datetime.fromisoformat(release["releaseDate"]).date()
        except Exception:continue
        if release_date<=today or (release_date-today).days>90 or title_key(release["title"]) in local_keys:continue
        upcoming.append({"id":"upcoming-"+re.sub(r"[^a-z0-9]+","-",release["title"].lower()).strip("-")[:70],"title":release["title"],"releaseDate":release["releaseDate"],"overview":"","poster":"","status":"upcoming","voteAverage":0,"rating":"","runtime":"","theaters":[],"news":[],"source":"The Numbers","confirmedThrough":"","leavingDate":"","leavingSoon":False})
        if len(upcoming)>=24:break
    rows.extend(upcoming)
    if rows:
        with ThreadPoolExecutor(max_workers=8) as pool:rows=[future.result() for future in as_completed([pool.submit(enrich_movie,row) for row in rows])]
        rows.sort(key=lambda m:(0 if m["status"]=="playing" else 1,-(datetime.fromisoformat(m["releaseDate"]).timestamp() if m.get("releaseDate") and m["status"]=="playing" else 0) if m["status"]=="playing" else (datetime.fromisoformat(m["releaseDate"]).timestamp() if m.get("releaseDate") else 9e18),m["title"].lower()))
    if not rows:
        try:
            text=fetch_text("https://www.boxofficemojo.com/weekend/");seen=set()
            for href,title in re.findall(r'<a[^>]+href="([^"]*/release/[^"]*)"[^>]*>(.*?)</a>',text,re.I|re.S):
                title=clean(title);key=title.lower()
                if not title or key in seen:continue
                seen.add(key);rows.append({"id":"bmojo-"+re.sub(r"[^a-z0-9]+","-",key).strip("-")[:70],"title":title,"releaseDate":"","overview":"","poster":"","status":"playing","voteAverage":0,"rating":"","runtime":"","theaters":[],"news":google_movie_news(title),"source":"Box Office Mojo","url":urllib.parse.urljoin("https://www.boxofficemojo.com/weekend/",href),"confirmedThrough":"","leavingDate":"","leavingSoon":False})
                if len(rows)>=24:break
        except Exception as exc:errors.append(f"fallback: {type(exc).__name__}: {exc}")
    return rows,"; ".join(errors)
