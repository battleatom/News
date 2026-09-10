from pathlib import Path

P = Path('index.html')
SCRIPT_ID = 'pull-stats-ui-v1'
SCRIPT = r'''<script id="pull-stats-ui-v1">
(function(){
  'use strict';
  const AUTO_PULL_MS=15*60*1000;
  let stats=null;
  let lastPullMs=0;
  function byId(id){return document.getElementById(id)}
  function currentTab(){try{return typeof active!=='undefined'?active:(window.active||'top')}catch(e){return window.active||'top'}}
  function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  function shortTime(ms){if(!ms)return '—';try{return new Date(ms).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}catch(e){return '—'}}
  function nextTime(){const target=Number(window.nextScheduledPull)||0;return target?shortTime(target):'—'}
  function btnBusy(){const b=byId('refresh');return !!b?.disabled||b?.dataset.refreshing==='1'}

  function ensureVisibleUI(){
    const btn=byId('refresh'),toolbar=btn?.closest('.toolbar');
    if(!btn||!toolbar)return;
    const onTop=currentTab()==='top';
    btn.hidden=!onTop;
    btn.type='button';btn.removeAttribute('onclick');
    btn.title='Show the next 10 unseen Top Stories and quietly check the full feed for updates';
    btn.setAttribute('aria-label','Show next unseen Top Stories');
    if(!btn.dataset.refreshStatsWired){
      btn.dataset.refreshStatsWired='1';
      btn.addEventListener('click',async function(){
        if(btn.disabled||currentTab()!=='top')return;
        btn.disabled=true;btn.dataset.refreshing='1';btn.textContent='⟳ Checking…';
        try{
          if(typeof window.cycleTopStoriesAndRefresh==='function')await window.cycleTopStoriesAndRefresh();
          else if(typeof window.refreshNewsFromPage==='function')await window.refreshNewsFromPage(false);
        }catch(e){console.error('Top Stories discovery refresh failed:',e)}
        finally{btn.disabled=false;btn.dataset.refreshing='';btn.textContent='↻ Next Top Stories';renderStats()}
      });
    }
    if(btn.dataset.refreshing!=='1')btn.textContent='↻ Next Top Stories';
    let panel=byId('pull-stats-ui');
    if(!panel){panel=document.createElement('div');panel.id='pull-stats-ui';panel.setAttribute('role','status');panel.setAttribute('aria-live','polite');toolbar.insertAdjacentElement('afterend',panel)}
    return panel;
  }

  function renderStats(failed=false,phase=''){
    const panel=ensureVisibleUI();if(!panel)return;
    const finalCount=stats?.finalCount??(typeof allItems!=='undefined'?allItems.length:0);
    panel.dataset.fetched=String(stats?.fetchedCount??'');
    panel.dataset.newCount=String(stats?.newCount??'');
    panel.dataset.duplicatesRemoved=String(stats?.duplicatesRemoved??'');
    const busy=btnBusy();panel.className=failed?'failed':(busy?'busy':'ready');
    if(failed){
      panel.innerHTML=`<strong>⚠ Update delayed</strong><span>•</span><span>Showing current feed</span><span>•</span><span>Last good feed ${escapeHtml(shortTime(lastPullMs))}</span>`;
      return;
    }
    panel.innerHTML=`<strong>✓ Live updates</strong><span>•</span><span>${finalCount} stories</span><span>•</span><span>Feed ${escapeHtml(shortTime(lastPullMs))}</span><span>•</span><span>Next check ${escapeHtml(nextTime())}</span>`;
  }

  async function loadStats(){
    try{
      const r=await fetch('update-stats.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);stats=await r.json();
      const parsed=Date.parse(stats.updatedAt);
      if(Number.isFinite(parsed)){
        const current=Number(window.lastSuccessfulPull)||0;
        lastPullMs=Math.max(parsed,current||0);
        if(!current||parsed>current){window.lastSuccessfulPull=parsed;window.nextScheduledPull=parsed+AUTO_PULL_MS}
      }
    }catch(e){}
    renderStats(false,'');
  }

  window.refreshPullStatsUI=function(failed,phase){renderStats(!!failed,phase||'')};
  window.syncTopDiscoveryButton=ensureVisibleUI;
  ensureVisibleUI();loadStats();
  const tabs=byId('tabs');
  if(tabs){
    tabs.addEventListener('click',()=>setTimeout(()=>{ensureVisibleUI();renderStats()},0));
    new MutationObserver(()=>{ensureVisibleUI()}).observe(tabs,{childList:true});
  }
  setInterval(loadStats,60000);
})();
</script>'''
STYLE = r'''<style id="pull-stats-ui-v1-style">
#pull-stats-ui{display:flex;flex-wrap:nowrap;align-items:center;gap:6px;margin:0;padding:5px 12px;border-bottom:1px solid var(--ui-line);background:#f8fafc;color:#475569;font-size:10px;line-height:1.25;font-weight:650;white-space:nowrap;overflow-x:auto;scrollbar-width:none}#pull-stats-ui::-webkit-scrollbar{display:none}#pull-stats-ui strong{color:#166534;font-weight:850}#pull-stats-ui.failed strong{color:#b91c1c}#pull-stats-ui.busy{color:#92400e}#pull-stats-ui.busy strong{color:#92400e}#refresh{font-weight:800!important}#refresh[hidden]{display:none!important}#refresh:disabled{opacity:.7;cursor:wait}@media(max-width:700px){#pull-stats-ui{font-size:9.5px;gap:5px;padding:5px 9px}#refresh{min-width:0!important}}
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
s=s.replace('<button id="refresh" onclick="loadNews(true)">↻ Refresh</button>','<button id="refresh" type="button">↻ Next Top Stories</button>',1)
s=s.replace('>↻ Refresh News</button>','>↻ Next Top Stories</button>',1)
s=s.replace('</head>',STYLE+'\n</head>',1)
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Simplified update status to one compact user-facing row and removed high-frequency status polling.')
