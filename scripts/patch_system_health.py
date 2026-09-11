from pathlib import Path

P=Path('index.html')
STYLE='''<style id="system-health-v1-style">
.sh-wrap{position:relative;display:inline-flex;align-items:center}.sh-button{display:inline-flex;align-items:center;gap:6px;border:0;background:transparent;color:inherit;font:inherit;font-weight:800;cursor:pointer;padding:5px 7px;border-radius:9px}.sh-button:hover{background:rgba(127,127,127,.09)}.sh-dot{width:9px;height:9px;border-radius:50%;background:#94a3b8;box-shadow:0 0 0 2px rgba(148,163,184,.14)}.sh-wrap.healthy .sh-dot,.sh-system.healthy i{background:#16a34a}.sh-wrap.degraded .sh-dot,.sh-system.degraded i{background:#eab308}.sh-wrap.partial .sh-dot,.sh-system.partial i{background:#f97316}.sh-wrap.critical .sh-dot,.sh-system.critical i{background:#dc2626}.sh-panel{position:absolute;z-index:50;top:calc(100% + 8px);left:0;width:min(360px,calc(100vw - 24px));padding:12px;border:1px solid var(--ui-line);border-radius:14px;background:#fff;color:#334155;box-shadow:0 14px 38px rgba(15,23,42,.18);font-size:11px}.sh-panel[hidden]{display:none}.sh-head{display:flex;justify-content:space-between;gap:10px;margin-bottom:8px}.sh-title{font-weight:900}.sh-code{font-family:monospace;font-weight:800}.sh-system{display:flex;align-items:center;gap:7px;padding:5px 0;border-top:1px solid rgba(127,127,127,.1)}.sh-system i{width:8px;height:8px;border-radius:50%;background:#94a3b8;flex:none}.sh-system span{flex:1}.sh-meta{margin-top:9px;padding-top:8px;border-top:1px solid var(--ui-line);color:#64748b;line-height:1.55}@media(prefers-color-scheme:dark){.sh-panel{background:#1c1c1e;color:#e5e7eb}.sh-meta{color:#a1a1aa}}@media(max-width:700px){.sh-label{font-size:9px}.sh-panel{position:fixed;top:74px;left:12px;right:12px;width:auto}}
</style>'''
SCRIPT=r'''<script id="system-health-v1">
(function(){
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=v=>{try{return new Date(v).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}catch(e){return '—'}};
 function ensure(){
  if(document.getElementById('system-health'))return document.getElementById('system-health');
  const toolbar=document.querySelector('.toolbar'),local=document.getElementById('local-status');if(!toolbar)return null;
  const w=document.createElement('div');w.id='system-health';w.className='sh-wrap';
  w.innerHTML='<button class="sh-button" type="button" aria-expanded="false"><span class="sh-dot"></span><span class="sh-label">System Health</span></button><div class="sh-panel" hidden></div>';
  if(local)toolbar.insertBefore(w,local);else toolbar.appendChild(w);
  const b=w.querySelector('.sh-button'),p=w.querySelector('.sh-panel');
  b.addEventListener('click',()=>{const open=p.hidden;p.hidden=!open;b.setAttribute('aria-expanded',String(open))});
  document.addEventListener('click',e=>{if(!w.contains(e.target)){p.hidden=true;b.setAttribute('aria-expanded','false')}});
  return w;
 }
 async function load(){
  const w=ensure();if(!w)return;let health=null,stats=null;
  try{const r=await fetch('refresh-health.json?ts='+Date.now(),{cache:'no-store'});if(r.ok)health=await r.json()}catch(e){}
  try{const r=await fetch('update-stats.json?ts='+Date.now(),{cache:'no-store'});if(r.ok)stats=await r.json()}catch(e){}
  let state=health?.status||'degraded';if(!['healthy','degraded','partial','critical'].includes(state))state='degraded';
  w.className='sh-wrap '+state;const panel=w.querySelector('.sh-panel');
  const systems=Array.isArray(health?.systems)?health.systems:[];
  const rows=systems.length?systems.map(x=>`<div class="sh-system ${esc(x.status||'degraded')}"><i></i><span><strong>${esc(x.name)}</strong> — ${esc(x.message||'Operational')}</span>${x.code?`<b class="sh-code">${esc(x.code)}</b>`:''}</div>`).join(''):'<div class="sh-system '+state+'"><i></i><span>'+esc(health?.message||'Health details unavailable')+'</span></div>';
  const code=health?.code?`<span class="sh-code">${esc(health.code)}</span>`:'';
  const counts=stats?`${esc(stats.fetchedCount??0)} fetched · ${esc(stats.newCount??0)} new · ${esc(stats.duplicatesRemoved??0)} duplicates removed · ${esc(stats.finalCount??'—')} final`:'';
  panel.innerHTML=`<div class="sh-head"><span class="sh-title">SYSTEM HEALTH — ${state.toUpperCase()}</span>${code}</div>${rows}<div class="sh-meta">${counts}${counts?'<br>':''}Last update: ${esc(fmt(stats?.updatedAt||health?.generatedAt))}</div>`;
  w.querySelector('.sh-button').title=(health?.message||'System health')+(health?.code?' · '+health.code:'');
 }
 document.readyState==='loading'?document.addEventListener('DOMContentLoaded',load,{once:true}):load();setInterval(load,60000);
})();
</script>'''
s=P.read_text(encoding='utf-8')
for ident,tag in [('system-health-v1-style','style'),('system-health-v1','script')]:
 a=s.find(f'<{tag} id="{ident}">')
 if a>=0:
  b=s.find(f'</{tag}>',a)
  if b>=0:s=s[:a]+s[b+len(tag)+3:]
s=s.replace('</head>',STYLE+'\n</head>',1).replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed expandable System Health indicator and diagnostic panel.')
