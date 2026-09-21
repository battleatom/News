from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old="fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'})"
new="fetch((()=>{const now=new Date(),a=new Date(now),b=new Date(now);a.setDate(a.getDate()-1);b.setDate(b.getDate()+14);const f=d=>`${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`;return `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64&dates=${f(a)}-${f(b)}&ts=${Date.now()}`})(),{cache:'no-store'})"
if old not in s:
    raise SystemExit('NFL scoreboard fetch signature not found; refusing silent patch')
s=s.replace(old,new,1)
s=s.replace(
    'Live:</strong> ESPN · refreshes every 30 sec · kickoff times use your device timezone · finals roll off at 6:00 AM local',
    'Live:</strong> ESPN · current + upcoming 14 days · refreshes every 30 sec · kickoff times use your device timezone · finals roll off at 6:00 AM local',
    1,
)
p.write_text(s,encoding='utf-8')
print('NFL scoreboard now requests current games plus the next 14 days.')
