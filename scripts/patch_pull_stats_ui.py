from pathlib import Path

P = Path('index.html')
MARKER = '<script id="pull-stats-ui-v1">'
SCRIPT = r'''<script id="pull-stats-ui-v1">
(function(){
  if(document.getElementById('pull-stats-ui-v1')) return;
  let pullStats=null;
  const originalPullStatusHtml=window.pullStatusHtml;
  function statsStatus(count,failed=false,phase=''){
    const root=document.getElementById('pull-status');if(!root)return;
    const last=typeof lastSuccessfulPull!=='undefined'&&lastSuccessfulPull?new Date(lastSuccessfulPull):null;
    const next=typeof nextScheduledPull!=='undefined'&&nextScheduledPull?nextScheduledPull?new Date(nextScheduledPull):null:null;
    const left=next&&typeof countdownText==='function'?countdownText(next.getTime()-Date.now()):'—';
    const fetched=pullStats?.fetchedCount ?? count ?? 0;
    const fresh=pullStats?.newCount ?? 0;
    const dup=pullStats?.duplicatesRemoved ?? 0;
    const finalCount=pullStats?.finalCount ?? count ?? 0;
    let lead=failed?'<span class="warn"><strong>⚠ Update failed</strong></span>':(typeof pullInProgress!=='undefined'&&pullInProgress?'<span class="busy"><strong>↻ Fetching news…</strong></span>':'<span class="ok"><strong>✓ Auto update active</strong></span>');
    let extra=phase?`<span>${esc(phase)}</span><span class="sep">·</span>`:'';
    root.innerHTML=`${lead}<span class="sep">·</span>${extra}<span>Last fetch: <strong>${last?formatDate(last.toISOString()):'—'}</strong></span><span class="sep">·</span><span>Next fetch: <strong>${left}</strong></span><span class="sep">·</span><span><strong>${fetched}</strong> fetched</span><span class="sep">·</span><span><strong>${fresh}</strong> new</span><span class="sep">·</span><span><strong>${dup}</strong> duplicates removed</span><span class="sep">·</span><span><strong>${finalCount}</strong> final</span>`;
  }
  window.pullStatusHtml=statsStatus;
  function wireRefreshButton(){
    const btn=document.getElementById('refresh');
    if(!btn || btn.dataset.refreshWired==='1') return;
    btn.dataset.refreshWired='1';
    btn.removeAttribute('onclick');
    btn.type='button';
    btn.title='Fetch the latest News feed now';
    btn.addEventListener('click',async()=>{
      if(typeof window.loadNews!=='function' || btn.disabled) return;
      const old=btn.textContent;
      btn.textContent='⟳ Refreshing…';
      btn.classList.add('refreshing');
      try{await window.loadNews(true);}finally{btn.textContent=old||'↻ Refresh News';btn.classList.remove('refreshing');}
    });
    if(btn.textContent.trim()==='↻ Refresh') btn.textContent='↻ Refresh News';
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
while MARKER in s:
    a=s.find(MARKER);b=s.find('</script>',a)
    if b<0:break
    s=s[:a]+s[b+9:]
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Made Refresh visibly change to Refreshing… while fetching and explicitly trigger loadNews(true).')
