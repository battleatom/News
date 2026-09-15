from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old="fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'})"
new="fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=64&ts='+Date.now(),{cache:'no-store'})"
if old not in s:
    if "scoreboard?limit=64&ts='" in s:
        print('NFL scoreboard current-week request already present.')
        raise SystemExit(0)
    raise SystemExit('NFL scoreboard fetch signature not found; refusing silent patch')
s=s.replace(old,new,1)
s=s.replace(
    'Live:</strong> ESPN · refreshes every 30 sec · kickoff times use your device timezone · finals roll off at 6:00 AM local',
    'Live:</strong> ESPN · current NFL week · refreshes every 30 sec · kickoff times use your device timezone · finals roll off at 6:00 AM local',
    1,
)
if 'dates=${f(a)}-${f(b)}' in s:
    raise SystemExit('Unsupported NFL date-range request remains in generated site.')
p.write_text(s,encoding='utf-8')
print('NFL scoreboard now uses ESPN current-week data.')
