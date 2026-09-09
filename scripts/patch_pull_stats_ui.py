from pathlib import Path

P = Path('index.html')
SCRIPT_ID = 'pull-stats-ui-v2'
SCRIPT = r'''<script id="pull-stats-ui-v2">
(function(){
  'use strict';
  const AUTO_PULL_MS=15*60*1000;
  let stats=null;
  let lastPullMs=0;
  function byId(id){return document.getElementById(id)}
  function safeFormatDate(v){try{return typeof window.formatDate==='function'?window.formatDate(v):new Date(v).toLocaleString()}catch(e){return String(v||'—')}}
  function currentNext(){return Number(window.nextScheduledPull)||0}
  function countdown(){
    const target=currentNext();
    if(!target)return '—';
    const sec=Math.max(0,Math.ceil((target-Date.now())/1000));
    if(sec<=0)return 'Updating…';
    const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;
    if(h)return `${h}h ${String(m).padStart(2,'0')}m`;
    if(m)return `${m}m ${String(s).padStart(2,'0')}s`;
    return `${s}s`;
  }
  function ensureVisibleUI(){
    const btn=byId('refresh'),toolbar=btn?.closest('.toolbar');
    if(!btn||!toolbar)return;
    btn.type='button';btn.removeAttribute('onclick');btn.title='Fetch the latest news feed now';btn.setAttribute('aria-label','Fetch the latest news feed now');btn.style.minWidth='122px';btn.style.fontWeight='800';btn.style.cursor='pointer';
    if(!btn.dataset.refreshStatsWired){
      btn.dataset.refreshStatsWired='1';
      btn.addEventListener('click',async function(){
        if(btn.disabled||typeof window.refreshNewsFromPage!=='function')return;
        btn.disabled=true;btn.dataset.refreshing='1';btn.textContent='⟳ Refreshing…';
        try{await window.refreshNewsFromPage(true)}catch(e){console.error('Manual news refresh failed:',e)}
        finally{btn.disabled=false;btn.dataset.refreshing='';btn.textContent='↻ Refresh News';renderStats()}
      });
    }
    if(btn.dataset.refreshing!=='1')btn.textContent='↻ Refresh News';
    let panel=byId('pull-stats-ui');
    if(!panel){panel=document.createElement('div');panel.id='pull-stats-ui';panel.setAttribute('role','status');panel.setAttribute('aria-live','polite');toolbar.insertAdjacentElement('afterend',panel)}
    return panel;
  }
  function renderStats(failed=false,phase=''){
    const panel=ensureVisibleUI();if(!panel)return;
    const fetched=stats?.fetchedCount??(typeof allItems!=='undefined'?allItems.length:0),fresh=stats?.newCount??0,dup=stats?.duplicatesRemoved??0,finalCount=stats?.finalCount??(typeof allItems!=='undefined'?allItems.length:0);
    const last=lastPullMs?safeFormatDate(new Date(lastPullMs).toISOString()):'—';
    const busy=btnBusy();panel.className=failed?'failed':(busy?'busy':'ready');
    if(failed){panel.innerHTML='⚠ <strong>News update failed</strong>'+(phase?' · '+escapeHtml(phase):'')+' · Existing feed preserved';return}
    panel.innerHTML=`<strong>✓ Auto update active</strong><span>•</span><span>${fetched} fetched</span><span>•</span><span>${fresh} new</span><span>•</span><span>${dup} duplicates removed</span><span>•</span><span>${finalCount} final</span><span>•</span><span>Last: ${escapeHtml(last)}</span><span>•</span><span>Next: ${escapeHtml(countdown())}</span>`;
  }
  function btnBusy(){const b=byId('refresh');return !!b?.disabled||b?.dataset.refreshing==='1'}
  function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  async function loadStats(){
    try{
      const r=await fetch('update-stats.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);stats=await r.json();
      const parsed=Date.parse(stats.updatedAt);
      if(Number.isFinite(parsed)){
        const current=Number(window.lastSuccessfulPull)||0;
        if(!current||parsed>current){
          lastPullMs=parsed;window.lastSuccessfulPull=parsed;window.nextScheduledPull=parsed+AUTO_PULL_MS;
        }else if(!lastPullMs){lastPullMs=current}
      }
      renderStats(false,'');
    }catch(e){renderStats(false,'')}
  }
  window.refreshPullStatsUI=function(failed,phase){renderStats(!!failed,phase||'')};
  ensureVisibleUI();loadStats();setInterval(ensureVisibleUI,1000);setInterval(renderStats,1000);setInterval(loadStats,60000);
})();
</script>'''
STYLE = r'''<style id="pull-stats-ui-v2-style">
#pull-stats-ui{display:flex;flex-wrap:wrap;align-items:center;gap:7px;margin:0;padding:7px 12px;border-bottom:1px solid var(--ui-line);background:#f8fafc;color:#475569;font-size:11px;line-height:1.4;font-weight:650}#pull-stats-ui strong{color:#166534;font-weight:850}#pull-stats-ui.failed strong{color:#b91c1c}#pull-stats-ui.busy{color:#92400e}#pull-stats-ui.busy strong{color:#92400e}#refresh{min-width:122px!important;font-weight:800!important}#refresh:disabled{opacity:.7;cursor:wait}@media(max-width:700px){#pull-stats-ui{font-size:10px;gap:5px}}
</style>'''
s=P.read_text(encoding='utf-8')
for marker in ('pull-stats-ui-v1','pull-stats-ui-v2'):
    while True:
        a=s.find('<script id="'+marker+'">')
        if a<0:break
        b=s.find('</script>',a)
        if b<0:break
        s=s[:a]+s[b+9:]
    while True:
        a=s.find('<style id="'+marker+'-style">')
        if a<0:break
        b=s.find('</style>',a)
        if b<0:break
        s=s[:a]+s[b+8:]
s=s.replace('<button id="refresh" onclick="loadNews(true)">↻ Refresh</button>','<button id="refresh" type="button">↻ Refresh News</button>',1)
s=s.replace('</head>',STYLE+'\n</head>',1)
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Synchronized the visible countdown with the canonical automatic refresh timer.')