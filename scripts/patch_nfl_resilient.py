from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# Patch the final NFL live fetch after earlier NFL patchers have run.
# V5.3's upcoming-window patch may emit an unsupported date-range request,
# so accept both the original live fetch and that generated variant.
original_block = "const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);const d=await r.json();"
range_block = "const r=await fetch((()=>{const now=new Date(),a=new Date(now),b=new Date(now);a.setDate(a.getDate()-1);b.setDate(b.getDate()+7);const f=d=>`${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`;return `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64&dates=${f(a)}-${f(b)}&ts=${Date.now()}`})(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);const d=await r.json();"
replacement = """let d=null,liveError=null;
   try{const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);d=await r.json();}catch(e){liveError=e;}
   if(!d?.events?.length){const r=await fetch('assets/nfl-scoreboard.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw liveError||new Error('cached scoreboard HTTP '+r.status);d=await r.json();}
   if(!d?.events?.length)throw liveError||new Error('NFL scoreboard contains no events');"""

count=0
for block in (range_block, original_block):
    if block in s:
        s=s.replace(block,replacement,1)
        count=1
        break

if count != 1:
    if "assets/nfl-scoreboard.json?ts=" in s and "liveError" in s:
        print('NFL resilient scoreboard fallback already present.')
        raise SystemExit(0)
    raise SystemExit('NFL live fetch block not found; refusing unsafe patch.')

# The broken range expression must never survive the final build.
if 'dates=${f(a)}-${f(b)}' in s:
    raise SystemExit('Unsupported NFL date-range request survived resilient patch.')

p.write_text(s,encoding='utf-8')
print('NFL renderer now uses the supported current-week scoreboard with cached fallback.')
