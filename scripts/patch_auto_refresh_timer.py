from pathlib import Path
import re

P = Path('index.html')
MARKER = '<script id="auto-refresh-timer-v2">'
SCRIPT = r'''<script id="auto-refresh-timer-v2">
(function(){
  'use strict';
  const INTERVAL=15*60*1000;
  const RETRY=60*1000;
  function removeLegacyTimers(s){
    s=s.replace(/setInterval\(\(\)=>loadNews\(false\),15\*60\*1000\);/g,'');
    s=s.replace(/setInterval\(\(\)\s*=>\s*loadNews\(false\)\s*,\s*15\s*\*\s*60\s*\*\s*1000\s*\);/g,'');
    return s;
  }
  function start(){
    if(window.__autoRefreshTimerV2)return;
    window.__autoRefreshTimerV2=true;
    function tick(){
      try{
        if(typeof window.pullInProgress!=='undefined' && window.pullInProgress)return;
        if(typeof window.nextScheduledPull!=='number' || !window.nextScheduledPull){
          const last=Number(window.lastSuccessfulPull)||0;
          window.nextScheduledPull=last?last+INTERVAL:Date.now()+INTERVAL;
        }
        if(Date.now() < window.nextScheduledPull)return;
        if(typeof window.refreshNewsFromPage!=='function')return;
        window.refreshNewsFromPage(false).then(function(){
          const last=Number(window.lastSuccessfulPull)||Date.now();
          window.nextScheduledPull=last+INTERVAL;
        }).catch(function(err){
          console.error('Automatic news refresh failed:',err);
          window.nextScheduledPull=Date.now()+RETRY;
        });
      }catch(e){
        console.error('Automatic refresh timer error:',e);
        window.nextScheduledPull=Date.now()+RETRY;
      }
    }
    setInterval(tick,1000);
    tick();
  }
  let s=PENDING_PAGE_PLACEHOLDER;
  if(s){}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
</script>'''

# The generated page is modified below; keep the patch itself independent of the page's current script layout.
s=P.read_text(encoding='utf-8')
# Remove all versions of this timer patch.
for marker in ('auto-refresh-timer-v1','auto-refresh-timer-v2'):
    while marker in s:
        a=s.find('<script id="'+marker+'">')
        if a<0: break
        b=s.find('</script>',a)
        if b<0: break
        s=s[:a]+s[b+9:]
# Remove the old 15-minute loadNews timer from the original page script.
s=re.sub(r'\s*setInterval\(\(\)\s*=>\s*loadNews\(false\)\s*,\s*15\s*\*\s*60\s*\*\s*1000\s*\);','',s)
# Inject the canonical timer without embedding the current page in this patch source.
script=SCRIPT.replace('PENDING_PAGE_PLACEHOLDER','false')
if '</body>' not in s: raise SystemExit('body not found')
s=s.replace('</body>',script+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed a single reset-safe 15-minute automatic refresh timer and removed the legacy timer.')