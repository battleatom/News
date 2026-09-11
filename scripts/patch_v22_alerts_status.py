from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# V2.2 owns the visible refresh-status panel. Remove older status controllers so
# only one script can update refresh state and metrics.
for tag, marker, close in (
    ('script', 'pull-stats-ui-v1', '</script>'),
    ('style', 'pull-stats-ui-v1-style', '</style>'),
    ('script', 'alerts-status-v22', '</script>'),
    ('style', 'alerts-status-v22-style', '</style>'),
):
    needle = f'<{tag} id="{marker}">'
    while needle in s:
        a = s.find(needle)
        b = s.find(close, a)
        if b < 0:
            break
        s = s[:a] + s[b + len(close):]

STYLE = r'''<style id="alerts-status-v22-style">
#status{display:none!important}
#pull-stats-ui{display:block!important;margin:0!important;padding:6px 11px!important;border-bottom:1px solid var(--ui-line)!important;background:#f8fafc!important;color:#475569!important;font-size:10px!important;line-height:1.28!important;font-weight:650!important;white-space:normal!important;overflow:visible!important}
#pull-stats-ui .status-line{display:flex;align-items:center;flex-wrap:wrap;gap:4px 7px;min-height:16px}
#pull-stats-ui .status-line+.status-line{margin-top:2px;color:#64748b}
#pull-stats-ui .status-state{font-weight:850;color:#166534}
#pull-stats-ui.busy .status-state{color:#b45309}
#pull-stats-ui.failed .status-state{color:#b91c1c}
#pull-stats-ui .status-new{font-weight:850;color:#dc2626}
#pull-stats-ui .sep{color:#cbd5e1}
.new-badge{display:inline-flex!important;align-items:center!important;margin-left:6px!important;padding:2px 6px!important;border-radius:999px!important;background:#dc2626!important;color:#fff!important;font-size:9px!important;line-height:1.25!important;font-weight:900!important;letter-spacing:.04em!important;vertical-align:middle!important;box-shadow:0 1px 4px rgba(220,38,38,.24)!important}
@media(max-width:700px){#pull-stats-ui{padding:6px 9px!important;font-size:9.5px!important}#pull-stats-ui .status-line{gap:3px 6px}}
@media(prefers-color-scheme:dark){#pull-stats-ui{background:#171719!important;color:#d1d1d6!important}#pull-stats-ui .status-line+.status-line{color:#a1a1aa}}
</style>'''

SCRIPT = r'''<script id="alerts-status-v22">
(function(){
  'use strict';
  const AUTO_MS=15*60*1000;
  let stats=null;
  let refreshState='scheduled';
  let tickTimer=null;
  let statsTimer=null;

  const byId=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function shortTime(ms){if(!ms)return '—';try{return new Date(ms).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}catch(e){return '—'}}
  function countdown(ms){
    const total=Math.max(0,Math.ceil(ms/1000));
    const m=Math.floor(total/60), sec=total%60;
    if(m>=60){const h=Math.floor(m/60),rm=m%60;return `${h}h ${rm}m`;}
    return `${m}m ${String(sec).padStart(2,'0')}s`;
  }
  function lastPull(){const fromStats=Date.parse(stats?.updatedAt||'')||0;return Math.max(fromStats,Number(window.lastSuccessfulPull)||0)}
  function nextPull(){
    let next=Number(window.nextScheduledPull)||0;
    const now=Date.now();
    if(next<=0){const last=lastPull();next=last?last+AUTO_MS:now+AUTO_MS;window.nextScheduledPull=next;}
    return next;
  }
  function ensurePanel(){
    let panel=byId('pull-stats-ui');
    if(panel)return panel;
    const toolbar=document.querySelector('.toolbar');if(!toolbar)return null;
    panel=document.createElement('div');panel.id='pull-stats-ui';panel.setAttribute('role','status');panel.setAttribute('aria-live','polite');toolbar.insertAdjacentElement('afterend',panel);return panel;
  }
  function stateLabel(){
    if(refreshState==='checking'||window.pullInProgress)return '↻ Auto refresh checking';
    if(refreshState==='retrying')return '⚠ Auto refresh retrying';
    const last=lastPull();if(last&&Date.now()-last>AUTO_MS*2.5)return '⚠ Feed update delayed';
    return '✓ Auto refresh active';
  }
  function renderStatus(){
    const panel=ensurePanel();if(!panel)return;
    const fetched=Number(stats?.fetchedCount)||0,newCount=Number(stats?.newCount)||0,dupes=Number(stats?.duplicatesRemoved)||0,shown=Number(stats?.finalCount)||(typeof allItems!=='undefined'?allItems.length:0);
    const last=lastPull(),next=nextPull(),remaining=next-Date.now();
    const failed=refreshState==='retrying'||(last&&Date.now()-last>AUTO_MS*2.5);
    const busy=refreshState==='checking'||window.pullInProgress;
    panel.className=failed?'failed':busy?'busy':'ready';
    panel.innerHTML=`<div class="status-line"><span class="status-state">${esc(stateLabel())}</span><span class="sep">•</span><span>Next in <strong>${esc(countdown(remaining))}</strong></span><span class="sep">•</span><span>Next ${esc(shortTime(next))}</span></div><div class="status-line"><span>Last fetch <strong>${esc(shortTime(last))}</strong></span><span class="sep">•</span><span>${fetched} fetched</span><span class="sep">•</span><span class="status-new">${newCount} new</span><span class="sep">•</span><span>${dupes} duplicates removed</span><span class="sep">•</span><span>${shown} shown</span></div>`;
  }

  async function loadStats(){
    try{
      const r=await fetch('update-stats.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);
      stats=await r.json();
      const parsed=Date.parse(stats.updatedAt||'');
      if(Number.isFinite(parsed)){
        window.lastSuccessfulPull=Math.max(Number(window.lastSuccessfulPull)||0,parsed);
        const now=Date.now(),next=Number(window.nextScheduledPull)||0;
        if(next<=now&&refreshState!=='retrying')window.nextScheduledPull=Math.max(parsed+AUTO_MS,now+1000);
      }
    }catch(e){console.warn('Update statistics unavailable:',e)}
    if(typeof window.decorateNewBadges==='function')window.decorateNewBadges();
    renderStatus();
  }

  function wireTopButton(){
    const btn=byId('refresh');if(!btn)return;
    const current=()=>{try{return typeof active!=='undefined'?active:(window.active||'top')}catch(e){return window.active||'top'}};
    btn.hidden=current()!=='top';btn.type='button';btn.textContent='↻ Next Top Stories';
    if(btn.dataset.v22Wired)return;btn.dataset.v22Wired='1';
    btn.addEventListener('click',async()=>{
      if(btn.disabled||current()!=='top')return;
      btn.disabled=true;btn.textContent='⟳ Checking…';
      try{if(typeof window.cycleTopStoriesAndRefresh==='function')await window.cycleTopStoriesAndRefresh();else if(typeof window.refreshNewsFromPage==='function')await window.refreshNewsFromPage(false)}catch(e){console.error(e)}
      finally{btn.disabled=false;btn.textContent='↻ Next Top Stories';renderStatus()}
    });
  }
  window.syncTopDiscoveryButton=function(){wireTopButton();renderStatus()};

  const originalRefresh=window.refreshNewsFromPage;
  if(typeof originalRefresh==='function'&&!originalRefresh.__v22Wrapped){
    const wrapped=async function(...args){
      const before=Number(window.lastSuccessfulPull)||0;refreshState='checking';renderStatus();
      try{return await originalRefresh.apply(this,args)}finally{
        const after=Number(window.lastSuccessfulPull)||0;
        refreshState=after>before?'scheduled':'retrying';
        if(refreshState==='retrying'&&Number(window.nextScheduledPull)<=Date.now())window.nextScheduledPull=Date.now()+60*1000;
        await loadStats();
      }
    };
    wrapped.__v22Wrapped=true;window.refreshNewsFromPage=wrapped;
  }

  const tabs=byId('tabs');if(tabs)tabs.addEventListener('click',()=>setTimeout(()=>{wireTopButton();renderStatus()},0));
  function tick(){renderStatus();tickTimer=setTimeout(tick,1000-(Date.now()%1000)+20)}
  function refreshStatsLoop(){void loadStats();statsTimer=setTimeout(refreshStatsLoop,60000)}
  wireTopButton();void loadStats();tick();statsTimer=setTimeout(refreshStatsLoop,60000);
  window.__alertsStatusV22=true;
})();
</script>'''

if '</head>' not in s or '</body>' not in s:
    raise SystemExit('Generated page is missing head/body closing tags')
s = s.replace('</head>', STYLE + '\n</head>', 1)
s = s.replace('</body>', SCRIPT + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Installed V2.2 refresh status, fetch metrics, countdown, and Top Stories controls without retired audio code.')
