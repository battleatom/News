(()=>{
  const refresh=document.getElementById('refresh-status'),weather=document.getElementById('weather-status');
  if(weather)weather.style.display='none';
  const style=document.createElement('style');style.textContent='.toolbar{align-items:flex-start;justify-content:flex-start;flex-wrap:wrap;gap:6px 8px;padding-bottom:7px}.local-status,.refresh-status{display:flex;align-items:center;flex-wrap:wrap;gap:6px;white-space:normal;text-align:left}.local-status .sep{display:none}.status-pill,#local-date,#local-time,#location-button{display:inline-flex;align-items:center;min-height:28px;padding:4px 9px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--muted);box-shadow:0 2px 7px rgba(15,23,42,.045);font-size:.64rem;font-weight:800;line-height:1.15;white-space:nowrap}#location-button{color:var(--text);text-decoration:none;cursor:pointer}#location-button:hover{border-color:var(--line-strong)}.status-pill.status-live{color:var(--good);background:rgba(21,128,61,.055);border-color:rgba(21,128,61,.16)}.status-pill.status-warn{color:var(--warn);background:rgba(180,83,9,.055);border-color:rgba(180,83,9,.16)}@media(max-width:760px){.toolbar{padding:0 12px 7px;gap:5px}.local-status,.refresh-status{gap:5px}.status-pill,#local-date,#local-time,#location-button{min-height:27px;padding:4px 8px;font-size:.6rem}}';document.head.appendChild(style);
  const fmt=seconds=>`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
  const feedSeconds=()=>{const span=5*60*1000,now=Date.now(),next=Math.floor(now/span)*span+span;return Math.max(0,Math.ceil((next-now)/1000))};
  function pillify(){
    if(!refresh)return;
    const raw=(refresh.textContent||'').trim();if(!raw)return;
    const match=raw.match(/Next check\s+(\d+):(\d{2})/i);if(match)refresh.dataset.browserSeconds=String(Number(match[1])*60+Number(match[2]));
    const parts=raw.split(' · ').map(x=>x.trim()).filter(Boolean).filter(part=>!/^Next check\b/i.test(part)&&!/^Next feed refresh\b/i.test(part));
    parts.push(`Next feed refresh ${fmt(feedSeconds())}`);
    const signature=parts.join(' · ');if(refresh.dataset.raw===signature&&refresh.querySelector('.status-pill'))return;refresh.dataset.raw=signature;
    refresh.innerHTML=parts.map(part=>{const live=/^(✓|↻)/.test(part),warn=/^(⚠|Delayed)/i.test(part);return `<span class="status-pill${live?' status-live':''}${warn?' status-warn':''}">${part}</span>`}).join('');
  }
  pillify();
  if(refresh)new MutationObserver(()=>{if(!refresh.querySelector('.status-pill'))pillify()}).observe(refresh,{childList:true,subtree:false});
  setInterval(()=>{if(!refresh)return;const pill=[...refresh.querySelectorAll('.status-pill')].find(el=>/^Next feed refresh\b/i.test(el.textContent||''));if(pill)pill.textContent=`Next feed refresh ${fmt(feedSeconds())}`},1000);
})();