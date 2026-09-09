from pathlib import Path

P = Path('index.html')
MARKER = '<script id="auto-refresh-timer-v1">'
SCRIPT = r'''<script id="auto-refresh-timer-v1">
(function(){
  'use strict';
  const INTERVAL=15*60*1000;
  function startAutoRefreshTimer(){
    if(window.__autoRefreshTimerV1)return;
    window.__autoRefreshTimerV1=true;
    setInterval(async function(){
      try{
        if(typeof pullInProgress!=='undefined' && pullInProgress)return;
        if(typeof nextScheduledPull==='undefined')return;
        if(!nextScheduledPull){
          if(typeof lastSuccessfulPull!=='undefined' && lastSuccessfulPull){
            nextScheduledPull=lastSuccessfulPull+INTERVAL;
          }else{
            nextScheduledPull=Date.now()+INTERVAL;
          }
        }
        if(Date.now()>=nextScheduledPull && typeof refreshNewsFromPage==='function'){
          await refreshNewsFromPage(false);
          if(typeof lastSuccessfulPull!=='undefined' && lastSuccessfulPull){
            nextScheduledPull=lastSuccessfulPull+INTERVAL;
          }else{
            nextScheduledPull=Date.now()+INTERVAL;
          }
        }
        if(typeof pullStatusHtml==='function' && typeof allItems!=='undefined')pullStatusHtml(allItems.length,false);
      }catch(e){console.error('Auto refresh timer error:',e);}
    },1000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',startAutoRefreshTimer);else startAutoRefreshTimer();
})();
</script>'''

s=P.read_text(encoding='utf-8')
while MARKER in s:
    a=s.find(MARKER); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]
if '</body>' not in s: raise SystemExit('body not found')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed reliable 15-minute automatic refresh timer.')
