(()=>{
  const tabs=document.getElementById('tabs'),feed=document.getElementById('feed'),refresh=document.getElementById('refresh-status');
  if(!tabs||!feed)return;
  const active=()=>!!tabs.querySelector('.tab[data-category="admin"][aria-selected="true"]');
  const fmt=seconds=>`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
  const feedSeconds=()=>{const span=5*60*1000,now=Date.now(),next=Math.floor(now/span)*span+span;return Math.max(0,Math.ceil((next-now)/1000))};
  const browserSeconds=()=>Math.max(0,Number(refresh?.dataset.browserSeconds||0));
  function ensure(){
    if(!active())return null;
    const wrap=feed.firstElementChild;if(!wrap)return null;
    let bar=document.getElementById('admin-refresh-pills');
    if(!bar){
      bar=document.createElement('div');bar.id='admin-refresh-pills';
      bar.style.cssText='display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 0';
      bar.innerHTML='<span data-feed-refresh style="display:inline-flex;align-items:center;gap:7px;min-height:30px;padding:5px 10px;border-radius:999px;border:1px solid rgba(21,128,61,.18);background:rgba(21,128,61,.06);color:#15803d;font-size:.62rem;font-weight:900;white-space:nowrap"></span><span data-browser-refresh style="display:inline-flex;align-items:center;gap:7px;min-height:30px;padding:5px 10px;border-radius:999px;border:1px solid rgba(37,99,235,.18);background:rgba(37,99,235,.06);color:#2563eb;font-size:.62rem;font-weight:900;white-space:nowrap"></span><button type="button" data-export="xml" style="appearance:none;display:inline-flex;align-items:center;justify-content:center;min-height:30px;padding:5px 12px;border-radius:999px;border:1px solid rgba(124,58,237,.22);background:rgba(124,58,237,.07);color:#7c3aed;font:inherit;font-size:.62rem;font-weight:900;white-space:nowrap;cursor:pointer">Export XML</button><button type="button" data-full-health-sweep style="appearance:none;display:inline-flex;align-items:center;justify-content:center;min-height:30px;padding:5px 12px;border-radius:999px;border:1px solid rgba(180,83,9,.24);background:rgba(180,83,9,.08);color:#b45309;font:inherit;font-size:.62rem;font-weight:900;white-space:nowrap;cursor:pointer">Full Health Sweep</button><button type="button" data-force-update style="appearance:none;display:inline-flex;align-items:center;justify-content:center;min-height:30px;padding:5px 12px;border-radius:999px;border:1px solid rgba(37,99,235,.24);background:rgba(37,99,235,.08);color:#2563eb;font:inherit;font-size:.62rem;font-weight:900;white-space:nowrap;cursor:pointer">Update Now</button>';
      const anchor=wrap.firstElementChild;anchor?.insertAdjacentElement('afterend',bar);
    }
    return bar;
  }
  function update(){
    const bar=ensure();if(!bar)return;
    const feedPill=bar.querySelector('[data-feed-refresh]'),browserPill=bar.querySelector('[data-browser-refresh]');
    if(feedPill)feedPill.textContent=`● Production Feed · 5m · ${fmt(feedSeconds())}`;
    if(browserPill)browserPill.textContent=`● Browser Sync · 1m · ${fmt(browserSeconds())}`;
  }
  new MutationObserver(()=>{if(active())queueMicrotask(update)}).observe(feed,{childList:true,subtree:false});
  tabs.addEventListener('click',e=>{if(e.target.closest('.tab[data-category="admin"]'))setTimeout(update,80)},true);
  document.addEventListener('click',async e=>{const b=e.target.closest('[data-full-health-sweep]');if(!b)return;if(b.disabled)return;const original=b.textContent;b.disabled=true;b.textContent='Sweeping all sources…';try{const r=await fetch('/api/admin/full-health-sweep',{method:'POST',cache:'no-store'}),d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||('HTTP '+r.status));b.textContent=`✓ ${d.healthy} healthy · ${d.failed} failed`;document.dispatchEvent(new CustomEvent('v6:fullhealthsweep',{detail:d}));setTimeout(()=>location.reload(),1400)}catch(err){b.textContent='Sweep failed';b.title=String(err?.message||err);setTimeout(()=>{b.textContent=original;b.disabled=false},3500)}},true);
  document.addEventListener('click',async e=>{const b=e.target.closest('[data-force-update]');if(!b)return;if(b.disabled)return;const original=b.textContent;b.disabled=true;b.textContent='Updating…';try{const r=await fetch('/api/admin/force-update',{method:'POST',cache:'no-store'}),d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||('HTTP '+r.status));b.textContent=`✓ ${d.recovered} recovered · ${d.failed} failed`;document.dispatchEvent(new CustomEvent('v6:forceupdate',{detail:d}));setTimeout(()=>location.reload(),1200)}catch(err){b.textContent='Update failed';b.title=String(err?.message||err);setTimeout(()=>{b.textContent=original;b.disabled=false},3000)}},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')setTimeout(update,40)});
  setInterval(()=>{if(active())update()},1000);
  setTimeout(update,180);
})();