from pathlib import Path
import re

P = Path('index.html')
MARKER = '<script id="auto-refresh-timer-v1">'
SCRIPT = r'''<script id="auto-refresh-timer-v1">
(function(){
  'use strict';
  const INTERVAL=15*60*1000;
  const RETRY=60*1000;
  function start(){
    if(window.__autoRefreshTimerV1)return;
    window.__autoRefreshTimerV1=true;
    function tick(){
      try{
        if(window.pullInProgress)return;
        if(typeof window.nextScheduledPull!=='number' || !window.nextScheduledPull){
          const last=Number(window.lastSuccessfulPull)||0;
          window.nextScheduledPull=last?last+INTERVAL:Date.now()+INTERVAL;
        }
        if(Date.now()<window.nextScheduledPull)return;
        if(typeof window.refreshNewsFromPage!=='function')return;
        const before=Number(window.lastSuccessfulPull)||0;
        window.refreshNewsFromPage(false).then(function(){
          const last=Number(window.lastSuccessfulPull)||0;
          if(last>before){
            window.nextScheduledPull=last+INTERVAL;
          }else{
            window.nextScheduledPull=Date.now()+RETRY;
          }
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
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
</script>'''

s=P.read_text(encoding='utf-8')
for marker in ('auto-refresh-timer-v1','auto-refresh-timer-v2'):
    while True:
        a=s.find('<script id="'+marker+'">')
        if a<0:break
        b=s.find('</script>',a)
        if b<0:break
        s=s[:a]+s[b+9:]
s=re.sub(r'\s*setInterval\(\(\)\s*=>\s*loadNews\(false\)\s*,\s*15\s*\*\s*60\s*\*\s*1000\s*\);','',s)
if '</body>' not in s: raise SystemExit('body not found')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed one reset-safe 15-minute automatic refresh timer with one-minute failure retry and removed the legacy scheduler.')