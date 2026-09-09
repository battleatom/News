from pathlib import Path

P = Path('index.html')
MARKER = '<script id="pull-stats-ui-v2">'
SCRIPT = r'''<style id="pull-stats-ui-v2-style">
#refresh{min-width:122px!important;font-weight:800!important;transition:transform .15s ease,opacity .15s ease}
#refresh.refreshing{opacity:.72;transform:scale(.98)}
#status{font-weight:700;min-width:0}
</style>
<script id="pull-stats-ui-v2">
(function(){
  if(document.getElementById('pull-stats-ui-v2')) return;
  let pullStats=null;
  const originalPullStatusHtml=window.pullStatusHtml;
  function statsStatus(count,failed=false,phase=''){
    const root=document.getElementById('pull-status');
    const inline=document.getElementById('status');
    if(!root && !inline)return;
    const last=typeof lastSuccessfulPull!=='undefined'&&lastSuccessfulPull?new Date(lastSuccessfulPull):null;
    const next=typeof nextScheduledPull!=='undefined'&&nextScheduledPull?new Date(nextScheduledPull):null;
    const left=next&&typeof countdownText==='function'?countdownText(next.getTime()-Date.now()):'—';
    const fetched=pullStats?.fetchedCount ?? count ?? 0;
    const fresh=pullStats?.newCount ?? 0;
    const dup=pullStats?.duplicatesRemoved ?? 0;
    const finalCount=pullStats?.finalCount ?? count ?? 0;
    const busy=typeof pullInProgress!=='undefined'&&pullInProgress;
    let lead=failed?'⚠ Update failed':(busy?'↻ Fetching news…':'✓ Auto update active');
    let detail=`${lead} · ${fetched} fetched · ${fresh} new · ${dup} duplicates removed · ${finalCount} final`;
    if(last)detail+=` · Last: ${formatDate(last.toISOString())}`;
    if(next)detail+=` · Next: ${left}`;
    if(inline){inline.textContent=detail;inline.title=phase||'News feed update status';inline.setAttribute('aria-live','polite');}
    if(root){
      let extra=phase?`<span>${esc(phase)}</span><span class="sep">·</span>`:'';
      root.innerHTML=`${failed?'<span class="warn"><strong>⚠ Update failed</strong></span>':(busy?'<span class="busy"><strong>↻ Fetching news…</strong></span>':'<span class="ok"><strong>✓ Auto update active</strong></span>')}<span class="sep">·</span>${extra}<span>Last fetch: <strong>${last?formatDate(last.toISOString()):'—'}</strong></span><span class="sep">·</span><span>Next fetch: <strong>${left}</strong></span><span class="sep">·</span><span><strong>${fetched}</strong> fetched</span><span class="sep">·</span><span><strong>${fresh}</strong> new</span><span class="sep">·</span><span><strong>${dup}</strong> duplicates removed</span><span class="sep">·</span><span><strong>${finalCount}</strong> final</span>`;
    }
  }
  window.pullStatusHtml=statsStatus;
  function wireRefreshButton(){
    const btn=document.getElementById('refresh');
    if(!btn)return;
    if(btn.dataset.refreshWired!=='2'){
      btn.dataset.refreshWired='2';
      btn.removeAttribute('onclick');
      btn.type='button';
      btn.title='Fetch the latest News feed now';
      btn.addEventListener('click',async()=>{
        if(typeof window.loadNews!=='function' || btn.disabled)return;
        btn.disabled=true;
        btn.textContent='⟳ Refreshing…';
        btn.classList.add('refreshing');
        try{await window.loadNews(true);}finally{btn.disabled=false;btn.textContent='↻ Refresh News';btn.classList.remove('refreshing');}
      });
    }
    if(!btn.disabled && !btn.classList.contains('refreshing'))btn.textContent='↻ Refresh News';
  }
  async function loadPullStats(){
    try{const r=await fetch('update-stats.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('stats '+r.status);pullStats=await r.json();statsStatus(allItems?.length||0,false);}
    catch(e){if(typeof originalPullStatusHtml==='function')originalPullStatusHtml(allItems?.length||0,false);}
  }
  wireRefreshButton();
  loadPullStats();
  setInterval(wireRefreshButton,1000);
  setInterval(loadPullStats,60*1000);
  setInterval(()=>statsStatus(allItems?.length||0,false),1000);
})();
</script>'''

s=P.read_text(encoding='utf-8')
# Remove all prior pull-stats scripts/styles so this patch is deterministic.
for marker in ('<script id="pull-stats-ui-v1">','<script id="pull-stats-ui-v2">'):
    while marker in s:
        a=s.find(marker);b=s.find('</script>',a)
        if b<0:break
        s=s[:a]+s[b+9:]
while '<style id="pull-stats-ui-v2-style">' in s:
    a=s.find('<style id="pull-stats-ui-v2-style">');b=s.find('</style>',a)
    if b<0:break
    s=s[:a]+s[b+8:]
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Forced the Refresh News button text, active refreshing state, and live pull statistics beside the button.')
