(()=>{
  const root=document.getElementById('refresh-status');
  if(!root)return;
  let busy=false;
  function pill(label,cls=''){
    const el=document.createElement('span');
    el.className=`status-pill ${cls}`.trim();
    el.dataset.poolMetric='1';
    el.textContent=label;
    return el;
  }
  async function update(){
    if(busy)return;busy=true;
    try{
      const r=await fetch(`/status.json?ts=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)return;
      const s=await r.json();
      const live=Number(s.visibleStoryCount??s.storyCount??0);
      const reserve=Number(s.reserveStoryCount??0);
      const total=Number(s.poolStoryCount??(live+reserve));
      root.querySelectorAll('[data-pool-metric="1"]').forEach(el=>el.remove());
      const old=[...root.querySelectorAll('.status-pill')].find(el=>/^\d[\d,]*\s+stories$/i.test((el.textContent||'').trim())||/^Live\s+/i.test((el.textContent||'').trim()));
      if(old){old.textContent=`Live ${live.toLocaleString()}`;old.dataset.poolMetric='1'}
      else root.prepend(pill(`Live ${live.toLocaleString()}`));
      const next=[...root.querySelectorAll('.status-pill')].find(el=>/^Next feed refresh/i.test(el.textContent||''));
      const pool=pill(`Pool ${total.toLocaleString()}`,'status-live');
      const reservePill=pill(`Reserve ${reserve.toLocaleString()}`);
      if(next){root.insertBefore(pool,next);root.insertBefore(reservePill,next)}
      else{root.append(pool,reservePill)}
    }catch{}finally{busy=false}
  }
  update();
  setInterval(update,30000);
  new MutationObserver(()=>setTimeout(update,80)).observe(root,{childList:true,subtree:false});
})();
