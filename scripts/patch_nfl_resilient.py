from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
old="const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);const d=await r.json();"
new="""let d=null,liveError=null;
   try{const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);d=await r.json();}catch(e){liveError=e;}
   if(!d?.events?.length){const r=await fetch('assets/nfl-scoreboard.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw liveError||new Error('cached scoreboard HTTP '+r.status);d=await r.json();}
   if(!d?.events?.length)throw liveError||new Error('NFL scoreboard contains no events');"""
if old not in s:
    raise SystemExit('Expected NFL live fetch block not found; refusing unsafe patch.')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('NFL renderer now falls back to repository-cached scoreboard data.')
