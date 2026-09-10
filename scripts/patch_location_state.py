from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')
old="localStorage.setItem('underreported-region',detectedRegion);localStorage.setItem('underreported-location',detectedLocation);"
new=old+"localStorage.setItem('underreported-state',code);"
if old in s and "underreported-state',code" not in s:
    s=s.replace(old,new,1)
elif "underreported-state',code" not in s:
    raise SystemExit('Could not persist detected state code from Region geolocation')
P.write_text(s,encoding='utf-8')
print('Persisted detected U.S. state code for state-aware legislation and Box Office.')
