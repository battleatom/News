from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')

MARKER='<script id="region-location-v2">'
while MARKER in s:
    a=s.find(MARKER);b=s.find('</script>',a)
    if b<0:break
    s=s[:a]+s[b+9:]

# The legacy Region patch calls its own geolocation provider immediately. Remove
# that initial call and install one canonical location bridge instead. The
# existing tab click handler keeps calling detectUserRegion(), which this bridge
# replaces at runtime.
if 'detectUserRegion();' in s:
    s=s.replace('detectUserRegion();','',1)

SCRIPT=r'''<script id="region-location-v2">
(function(){
  'use strict';
  async function sharedRegionLocation(){
    try{
      if(!window.UnderreportedLocation?.get)throw new Error('Shared location service unavailable');
      const loc=await window.UnderreportedLocation.get();
      const code=String(loc?.state||'').replace(/^US-/,'').toUpperCase();
      if(code&&typeof stateRegion!=='undefined'&&stateRegion[code])detectedRegion=stateRegion[code];
      if(loc?.label)detectedLocation=loc.label;
      try{
        localStorage.setItem('underreported-region',detectedRegion);
        if(detectedLocation)localStorage.setItem('underreported-location',detectedLocation);
        if(code)localStorage.setItem('underreported-state',code);
      }catch(e){}
      if(typeof buildTabs==='function')buildTabs();
      if(typeof active!=='undefined'&&active==='region'&&typeof render==='function'&&typeof allItems!=='undefined')render(allItems);
    }catch(e){
      console.warn('Regional location unavailable:',e);
      if(typeof buildTabs==='function')buildTabs();
    }
  }
  detectUserRegion=sharedRegionLocation;
  sharedRegionLocation();
})();
</script>'''

if '</body>' not in s:raise SystemExit('Missing </body>')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Regional tab now uses the shared Underreported location service and persists one canonical state/location.')
