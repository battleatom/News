from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# Patch the final NFL live fetch after earlier NFL patchers have run.
# V5.3's upcoming-window patch may emit an unsupported date-range request,
# so accept both the original live fetch and that generated variant.
original_block = "const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);const d=await r.json();"
range_block = "const r=await fetch((()=>{const now=new Date(),a=new Date(now),b=new Date(now);a.setDate(a.getDate()-1);b.setDate(b.getDate()+7);const f=d=>`${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`;return `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64&dates=${f(a)}-${f(b)}&ts=${Date.now()}`})(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);const d=await r.json();"
replacement = """let liveData=null,cacheData=null,liveError=null,cacheError=null;
   try{const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);liveData=await r.json();}catch(e){liveError=e;}
   try{const r=await fetch('assets/nfl-scoreboard.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('cached scoreboard HTTP '+r.status);cacheData=await r.json();}catch(e){cacheError=e;}
   const gameKey=ev=>{const c=ev?.competitions?.[0],teams=c?.competitors||[],a=teams.find(t=>t.homeAway==='away'),h=teams.find(t=>t.homeAway==='home'),t=Date.parse(ev?.date||'');return `${a?.team?.abbreviation||''}|${h?.team?.abbreviation||''}|${Number.isFinite(t)?Math.round(t/60000):ev?.date||''}`;};
   const merged=new Map();
   for(const ev of (cacheData?.events||[])){const k=gameKey(ev);if(k)merged.set(k,ev);}
   for(const ev of (liveData?.events||[])){const k=gameKey(ev);if(k)merged.set(k,ev);}
   const d={...(cacheData||{}),...(liveData||{}),events:[...merged.values()]};
   if(!d.events.length)throw liveError||cacheError||new Error('NFL scoreboard contains no events');"""

count=0
for block in (range_block, original_block):
    if block in s:
        s=s.replace(block,replacement,1)
        count=1
        break

if count != 1:
    if "const merged=new Map();" in s and "assets/nfl-scoreboard.json?ts=" in s:
        print('NFL merged live + cached scoreboard loader already present.')
        raise SystemExit(0)
    raise SystemExit('NFL live fetch block not found; refusing unsafe patch.')

# The broken range expression must never survive the final build.
if 'dates=${f(a)}-${f(b)}' in s:
    raise SystemExit('Unsupported NFL date-range request survived resilient patch.')

p.write_text(s,encoding='utf-8')
print('NFL renderer now merges live ESPN data with the cached upcoming schedule.')
