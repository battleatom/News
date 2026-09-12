from pathlib import Path
import re

P=Path('index.html')
SCRIPT=r'''<script id="mobile-countdown-live-v4">
(function(){
  'use strict';
  function fmt(){
    const target=Number(window.nextScheduledPull)||0;
    if(!target)return '';
    const total=Math.max(0,Math.ceil((target-Date.now())/1000));
    const h=Math.floor(total/3600),m=Math.floor((total%3600)/60),s=total%60;
    return h?`${h}h ${String(m).padStart(2,'0')}m`:`${m}m ${String(s).padStart(2,'0')}s`;
  }
  function tick(){
    const el=document.getElementById('v3-auto-status');
    if(!el)return;
    const value=fmt();
    if(!value)return;
    el.dataset.countdown=value;
    const parts=String(el.textContent||'').split(' · ').filter(Boolean);
    if(parts.length){
      if(/^(?:\d+h\s+)?\d+m\s+\d+s$/.test(parts[parts.length-1]))parts[parts.length-1]=value;
      else parts.push(value);
      el.textContent=parts.join(' · ');
    }
  }
  if(window.__mobileCountdownLiveV4)clearInterval(window.__mobileCountdownLiveV4);
  window.__mobileCountdownLiveV4=setInterval(tick,250);
  tick();
})();
</script>'''
s=P.read_text(encoding='utf-8')
s=re.sub(r'<script id="mobile-countdown-live-v4">.*?</script>\s*','',s,flags=re.S)
if '</body>' not in s: raise SystemExit('Generated page is missing </body>')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed V4 mobile live-countdown stabilizer.')
