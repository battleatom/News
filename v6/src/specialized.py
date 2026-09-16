from __future__ import annotations
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

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

def collect_nfl()->tuple[list[dict],str]:
    try:
        payload=fetch_json("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard");rows=[]
        for event in payload.get("events",[]):
            competition=(event.get("competitions") or [{}])[0];teams=[]
            for comp in competition.get("competitors") or []:
                team=comp.get("team") or {};teams.append({"name":team.get("displayName") or team.get("shortDisplayName") or "","abbr":team.get("abbreviation") or "","score":comp.get("score") or "","homeAway":comp.get("homeAway") or "","logo":team.get("logo") or "","color":team.get("color") or ""})
            state=((event.get("status") or {}).get("type") or {}).get("state") or ""
            plays=[]
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

MARKETS=[("^GSPC","S&P 500"),("^DJI","Dow"),("^IXIC","Nasdaq"),("BTC-USD","Bitcoin"),("GC=F","Gold"),("CL=F","Oil")]
def collect_markets()->tuple[list[dict],str]:
    rows=[];errors=[]
    for symbol,label in MARKETS:
        try:
            url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol,safe="")+"?range=5d&interval=1d"
            result=((fetch_json(url).get("chart") or {}).get("result") or [{}])[0];meta=result.get("meta") or {};price=meta.get("regularMarketPrice")
            prev=meta.get("chartPreviousClose") or meta.get("previousClose") or meta.get("regularMarketPreviousClose")
            if price is None:
                closes=(((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []);valid=[x for x in closes if isinstance(x,(int,float))]
                if valid:price=valid[-1];prev=valid[-2] if len(valid)>1 else prev
            if price is None:continue
            change=((float(price)-float(prev))/float(prev)*100) if prev else 0
            rows.append({"symbol":symbol,"label":label,"price":round(float(price),2),"previousClose":round(float(prev),2) if prev else None,"changePct":change,"currency":meta.get("currency") or "USD","marketState":meta.get("marketState") or ""})
        except Exception as exc:errors.append(f"{symbol}: {type(exc).__name__}")
    return rows,"; ".join(errors)

SHOWTIMES_SLUG=os.environ.get("BOXOFFICE_CITY_SLUG","farmington-nm").strip() or "farmington-nm"
SHOWTIMES_LABEL=os.environ.get("BOXOFFICE_CITY_LABEL","Farmington, NM").strip() or "Farmington, NM"
SHOWTIMES_URL=f"https://www.showtimes.com/movie-times/{SHOWTIMES_SLUG}/"
RELEASE_URL=f"https://www.the-numbers.com/movies/release-schedule/{datetime.now(timezone.utc).year}"

def parse_local_showtimes(page:str)->list[dict]:
    blocks=list(re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2[^>]*>|</main>|</body>)",page,re.I|re.S));current="";rows=[]
    for match in blocks:
        heading_html=match.group(1);heading=clean(heading_html);body=clean(match.group(2))
        if heading.lower().startswith(("allen theatres","amc ","regal ","cinemark ","harkins ")):
            current=heading;continue
        times=re.findall(r"\b(?:[1-9]|1[0-2]):[0-5]\d\s*(?:am|pm)\b",body,re.I)
        if not current or not heading or not times:continue
        rating=(re.search(r"\b(G|PG|PG-13|R|NC-17|NR)\b",body) or [None,""])[1]
        runtime=(re.search(r"\b(\d+h\s*\d+m|\d+h|\d+m)\b",body) or [None,""])[1]
        rows.append({"title":heading.replace(" Watch Trailer","").strip(),"theater":current,"rating":rating,"runtime":runtime,"showtimes":list(dict.fromkeys(times))})
    return rows

def parse_release_schedule(page:str)->list[dict]:
    year=datetime.now(timezone.utc).year;out=[];seen=set()
    for raw in re.findall(r"<tr[^>]*>(.*?)</tr>",page,re.I|re.S):
        cells=[clean(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>",raw,re.I|re.S)]
        if len(cells)<2:continue
        joined=" | ".join(cells);dm=re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})",joined,re.I)
        if not dm:continue
        try:release=datetime.strptime(f"{dm.group(1)} {dm.group(2)} {year}","%B %d %Y").date()
        except ValueError:continue
        title=next((c for c in cells if c and not re.search(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\b",c,re.I) and not c.isdigit()),"")
        title=re.sub(r"\s*\([^)]*(?:Wide|Limited|IMAX|re-release|Special Engagement|Event)[^)]*\)\s*$","",title,flags=re.I).strip();key=(title.lower(),release.isoformat())
        if not title or key in seen:continue
        seen.add(key);out.append({"title":title,"releaseDate":release.isoformat()})
    return out

def google_movie_news(title:str)->list[dict]:
    try:
        q=urllib.parse.quote(f'"{title}" movie when:30d');root=ET.fromstring(fetch_text(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"));rows=[]
        for item in root.findall(".//item")[:3]:
            t=clean(item.findtext("title"));link=clean(item.findtext("link"));source=clean(item.findtext("source"));pub=clean(item.findtext("pubDate"))
            if t and link:rows.append({"title":t,"link":link,"source":source,"pubDate":pub})
        return rows
    except Exception:return []

def wiki_movie(title:str)->dict:
    for candidate in (f"{title} (film)",f"{title} ({datetime.now(timezone.utc).year} film)",title):
        try:
            d=fetch_json("https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(candidate.replace(" ","_")));extract=clean(d.get("extract") or "");desc=clean(d.get("description") or "").lower()
            if extract and any(k in f" {desc} {extract[:250].lower()} " for k in (" film "," movie "," motion picture "," directed by "," starring "," documentary "," animated ")):
                return{"overview":extract,"poster":((d.get("thumbnail") or {}).get("source") or "")}
        except Exception:continue
    return{"overview":"","poster":""}

def collect_boxoffice()->tuple[list[dict],str]:
    errors=[];movies={};today=datetime.now(timezone.utc).date()
    try:
        for row in parse_local_showtimes(fetch_text(SHOWTIMES_URL)):
            key=row["title"].lower();movie=movies.setdefault(key,{"id":"local-"+re.sub(r"[^a-z0-9]+","-",key).strip("-")[:70],"title":row["title"],"releaseDate":"","overview":"","poster":"","status":"playing","voteAverage":0,"rating":row.get("rating","") ,"runtime":row.get("runtime","") ,"theaters":[],"news":[],"source":"Showtimes.com"});movie["theaters"].append({"name":row["theater"],"showtimes":row["showtimes"]})
    except Exception as exc:errors.append(f"showtimes: {type(exc).__name__}: {exc}")
    try:
        releases=parse_release_schedule(fetch_text(RELEASE_URL))
        for row in releases:
            try:release=datetime.fromisoformat(row["releaseDate"]).date()
            except Exception:continue
            if release<today or (release-today).days>90:continue
            key=row["title"].lower()
            if key in movies:movies[key]["releaseDate"]=row["releaseDate"];continue
            movies[key]={"id":"upcoming-"+re.sub(r"[^a-z0-9]+","-",key).strip("-")[:70],"title":row["title"],"releaseDate":row["releaseDate"],"overview":"","poster":"","status":"upcoming","voteAverage":0,"rating":"","runtime":"","theaters":[],"news":[],"source":"The Numbers"}
            if sum(1 for x in movies.values() if x["status"]=="upcoming")>=24:break
    except Exception as exc:errors.append(f"releases: {type(exc).__name__}: {exc}")
    rows=list(movies.values())[:60]
    def enrich(movie:dict)->dict:
        movie.update(wiki_movie(movie["title"]));movie["news"]=google_movie_news(movie["title"]);return movie
    if rows:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures=[pool.submit(enrich,row) for row in rows];rows=[f.result() for f in as_completed(futures)]
        rows.sort(key=lambda m:(0 if m["status"]=="playing" else 1, -(datetime.fromisoformat(m["releaseDate"]).timestamp() if m.get("releaseDate") and m["status"]=="playing" else 0) if m["status"]=="playing" else (datetime.fromisoformat(m["releaseDate"]).timestamp() if m.get("releaseDate") else 9e18),m["title"].lower()))
    if not rows:
        try:
            text=fetch_text("https://www.boxofficemojo.com/weekend/");seen=set()
            for href,title in re.findall(r'<a[^>]+href="([^"]*/release/[^"]*)"[^>]*>(.*?)</a>',text,re.I|re.S):
                title=clean(title);key=title.lower()
                if not title or key in seen:continue
                seen.add(key);rows.append({"id":"bmojo-"+re.sub(r"[^a-z0-9]+","-",key).strip("-")[:70],"title":title,"releaseDate":"","overview":"","poster":"","status":"playing","voteAverage":0,"rating":"","runtime":"","theaters":[],"news":google_movie_news(title),"source":"Box Office Mojo","url":urllib.parse.urljoin("https://www.boxofficemojo.com/weekend/",href)})
                if len(rows)>=24:break
        except Exception as exc:errors.append(f"fallback: {type(exc).__name__}: {exc}")
    return rows,"; ".join(errors)
