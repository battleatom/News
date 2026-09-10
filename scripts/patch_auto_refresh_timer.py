from pathlib import Path
import re

P = Path('index.html')
SCRIPT = r'''<script id="auto-refresh-timer-v1">
(function(){
  'use strict';
  const INTERVAL=15*60*1000;
  const RETRY=60*1000;
  const BUSY_RETRY=30*1000;
  let timer=null;

  function schedule(delay){
    clearTimeout(timer);
    timer=setTimeout(run,Math.max(1000,Number(delay)||1000));
    window.__autoRefreshTimeout=timer;
  }

  function ensureNextPull(){
    if(typeof window.nextScheduledPull!=='number' || !window.nextScheduledPull){
      const last=Number(window.lastSuccessfulPull)||0;
      window.nextScheduledPull=last?last+INTERVAL:Date.now()+INTERVAL;
    }
    return window.nextScheduledPull;
  }

  async function run(){
    try{
      const due=ensureNextPull();
      if(window.pullInProgress){schedule(BUSY_RETRY);return;}
      if(Date.now()<due){schedule(due-Date.now());return;}
      if(typeof window.refreshNewsFromPage!=='function'){schedule(RETRY);return;}
      const before=Number(window.lastSuccessfulPull)||0;
      try{await window.refreshNewsFromPage(false);}catch(err){console.error('Automatic news refresh failed:',err);}
      const last=Number(window.lastSuccessfulPull)||0;
      window.nextScheduledPull=last>before?last+INTERVAL:Date.now()+RETRY;
      schedule(window.nextScheduledPull-Date.now());
    }catch(err){
      console.error('Automatic refresh scheduler error:',err);
      window.nextScheduledPull=Date.now()+RETRY;
      schedule(RETRY);
    }
  }

  function start(){
    if(window.__autoRefreshTimerV1)return;
    window.__autoRefreshTimerV1=true;
    const due=ensureNextPull();
    schedule(Math.max(1000,due-Date.now()));
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

# Remove legacy competing schedulers before installing the single timeout-based scheduler.
s=re.sub(r'\s*setInterval\(\(\)\s*=>\s*loadNews\(false\)\s*,\s*15\s*\*\s*60\s*\*\s*1000\s*\);','',s)
s=re.sub(r'\s*setInterval\(\(\)\s*=>\s*\{\s*if\(lastSuccessfulPull\s*&&\s*Date\.now\(\)\s*>=\s*nextScheduledPull\s*&&\s*!pullInProgress\)\s*\{\s*refreshNewsFromPage\(false\);\s*\}\s*\}\s*,\s*(?:1000|5000)\s*\);','',s)
if '</body>' not in s: raise SystemExit('body not found')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed one timeout-based 15-minute automatic refresh scheduler and removed competing polling schedulers.')
