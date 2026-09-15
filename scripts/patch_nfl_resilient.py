from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# Patch the fetch inside the final NFL live script after all earlier NFL patchers
# have run. Match the ESPN request structurally so small changes in neighboring
# NFL patchers do not break the deterministic build.
pattern = re.compile(
    r"const r=await fetch\('https://site\.api\.espn\.com/apis/site/v2/sports/football/nfl/scoreboard\?limit=32&ts='\+Date\.now\(\),\{cache:'no-store'\}\);"
    r"if\(!r\.ok\)throw new Error\('scoreboard HTTP '\+r\.status\);"
    r"const d=await r\.json\(\);"
)
replacement = """let d=null,liveError=null;
   try{const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);d=await r.json();}catch(e){liveError=e;}
   if(!d?.events?.length){const r=await fetch('assets/nfl-scoreboard.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw liveError||new Error('cached scoreboard HTTP '+r.status);d=await r.json();}
   if(!d?.events?.length)throw liveError||new Error('NFL scoreboard contains no events');"""

s2,count=pattern.subn(replacement,s,count=1)
if count != 1:
    # Idempotency: a previously patched build is already valid.
    if "assets/nfl-scoreboard.json?ts=" in s and "liveError" in s:
        print('NFL resilient scoreboard fallback already present.')
        raise SystemExit(0)
    raise SystemExit(f'Expected exactly one NFL live fetch block; found {count}. Refusing unsafe patch.')

p.write_text(s2,encoding='utf-8')
print('NFL renderer now falls back to repository-cached scoreboard data.')
