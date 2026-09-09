from pathlib import Path

P = Path('index.html')
SCRIPT_ID = 'pull-stats-ui-v1'
MARKER = f'<script id="{SCRIPT_ID}">'

# Keep this patch idempotent: remove any previous copy, then install one canonical copy.
SCRIPT = r'''<script id="pull-stats-ui-v1">
(function(){
  'use strict';
  function byId(id){return document.getElementById(id)}
  function safeFormatDate(v){
    try{ if(typeof window.formatDate==='function') return window.formatDate(v); return new Date(v).toLocaleString(); }
    catch(e){ return String(v||'—'); }
  }
  function countdown(){
    try{
      if(typeof window.nextScheduledPull!=='undefined' && window.nextScheduledPull && typeof window.countdownText==='function')
        return window.countdownText(window.nextScheduledPull-Date.now());
    }catch(e){}
    return '—';
  }
  function ensureVisibleUI(){
    const btn=byId('refresh');
    const toolbar=btn?.closest('.toolbar');
    if(!btn || !toolbar) return;

    // Make the intended control unmistakable even if another script changes its text later.
    btn.type='button';
    btn.removeAttribute('onclick');
    btn.title='Fetch the latest news feed now';
    btn.setAttribute('aria-label','Fetch the latest news feed now');
    btn.style.minWidth='122px';
    btn.style.fontWeight='800';
    btn.style.cursor='pointer';
    if(!btn.dataset.refreshStatsWired){
      btn.dataset.refreshStatsWired='1';
      btn.addEventListener('click',async function(){
        if(btn.disabled || typeof window.loadNews!=='function') return;
        btn.disabled=true;
        btn.dataset.refreshing='1';
        btn.textContent='⟳ Refreshing…';
        try{ await window.loadNews(true); }
        catch(e){ console.error('Manual news refresh failed:',e); }
        finally{
          btn.disabled=false;
          btn.dataset.refreshing='';
          btn.textContent='↻ Refresh News';
          renderStats();
        }
      });
    }
    if(btn.dataset.refreshing!=='1') btn.textContent='↻ Refresh News';

    let panel=byId('pull-stats-ui');
    if(!panel){
      panel=document.createElement('div');
      panel.id='pull-stats-ui';
      panel.setAttribute('role','status');
      panel.setAttribute('aria-live','polite');
      toolbar.insertAdjacentElement('afterend',panel);
    }
    return panel;
  }
  let stats=null;
  function renderStats(failed=false,phase=''){
    const panel=ensureVisibleUI();
    if(!panel)return;
    const fetched=stats?.fetchedCount ?? (typeof allItems!=='undefined'?allItems.length:0);
    const fresh=stats?.newCount ?? 0;
    const dup=stats?.duplicatesRemoved ?? 0;
    const finalCount=stats?.finalCount ?? (typeof allItems!=='undefined'?allItems.length:0);
    let last='—';
    try{if(typeof lastSuccessfulPull!=='undefined'&&lastSuccessfulPull)last=safeFormatDate(lastSuccessfulPull)}catch(e){}
    const busy=btnBusy();
    panel.className=failed?'failed':(busy?'busy':'ready');
    if(failed){
      panel.innerHTML='⚠ <strong>News update failed</strong>'+(phase?' · '+escapeHtml(phase):'')+' · Existing feed preserved';
      return;
    }
    panel.innerHTML=`<strong>✓ Auto update active</strong><span>•</span><span>${fetched} fetched</span><span>•</span><span>${fresh} new</span><span>•</span><span>${dup} duplicates removed</span><span>•</span><span>${finalCount} final</span><span>•</span><span>Last: ${escapeHtml(last)}</span><span>•</span><span>Next: ${escapeHtml(countdown())}</span>`;
  }
  function btnBusy(){const b=byId('refresh');return !!b?.disabled || b?.dataset.refreshing==='1'}
  function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  async function loadStats(){
    try{
      const r=await fetch('update-stats.json?ts='+Date.now(),{cache:'no-store'});
      if(!r.ok)throw new Error('HTTP '+r.status);
      stats=await r.json();
      renderStats(false,'');
    }catch(e){ renderStats(false,''); }
  }
  // Expose a stable hook for the site's canonical pull-status function.
  window.refreshPullStatsUI=function(failed,phase){renderStats(!!failed,phase||'')};
  ensureVisibleUI();
  loadStats();
  setInterval(ensureVisibleUI,1000);
  setInterval(renderStats,1000);
  setInterval(loadStats,60000);
})();
</script>'''

STYLE = r'''<style id="pull-stats-ui-v1-style">
#pull-stats-ui{display:flex;flex-wrap:wrap;align-items:center;gap:7px;margin:0;padding:7px 12px;border-bottom:1px solid var(--ui-line);background:#f8fafc;color:#475569;font-size:11px;line-height:1.4;font-weight:650}
#pull-stats-ui strong{color:#166534;font-weight:850}
#pull-stats-ui.failed strong{color:#b91c1c}
#pull-stats-ui.busy{color:#92400e}
#pull-stats-ui.busy strong{color:#92400e}
#refresh{min-width:122px!important;font-weight:800!important}
#refresh:disabled{opacity:.7;cursor:wait}
@media(max-width:700px){#pull-stats-ui{font-size:10px;gap:5px}}
</style>'''

s = P.read_text(encoding='utf-8')
# Remove every prior pull-stats script/style version so this patch cannot stack copies.
for marker in ('pull-stats-ui-v1','pull-stats-ui-v2'):
    while True:
        a=s.find(f'<script id="{marker}">')
        if a < 0: break
        b=s.find('</script>',a)
        if b < 0: break
        s=s[:a]+s[b+9:]
    while True:
        a=s.find(f'<style id="{marker}-style">')
        if a < 0: break
        b=s.find('</style>',a)
        if b < 0: break
        s=s[:a]+s[b+8:]

# Static fallback: users should see the changed button even before JavaScript runs.
s=s.replace('<button id="refresh" onclick="loadNews(true)">↻ Refresh</button>', '<button id="refresh" type="button">↻ Refresh News</button>', 1)
if '<div id="pull-stats-ui"' not in s:
    s=s.replace('</div><div class="markets"', '</div><div id="pull-stats-ui" role="status" aria-live="polite" class="ready"><strong>✓ Auto update active</strong><span>•</span><span>Loading pull statistics…</span></div><div class="markets"', 1)

s=s.replace('</head>', STYLE+'\n</head>',1)
s=s.replace('</body>', SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed visible Refresh News button and pull-statistics panel.')
