(()=>{
  const tabs=document.getElementById('tabs');
  const feed=document.getElementById('feed');
  if(!tabs||!feed)return;

  const active=()=>!!tabs.querySelector('.tab[data-category="admin"][aria-selected="true"]');
  const stateColor={green:'#15803d',yellow:'#b45309',red:'#b91c1c'};
  let busy=false;

  async function getJson(path){
    const started=performance.now();
    try{
      const r=await fetch(`${path}${path.includes('?')?'&':'?'}ts=${Date.now()}`,{cache:'no-store'});
      const data=await r.json().catch(()=>null);
      return{ok:r.ok,ms:Math.round(performance.now()-started),status:r.status,data};
    }catch(error){
      return{ok:false,ms:Math.round(performance.now()-started),status:0,error:String(error?.message||error)};
    }
  }

  function savedLocation(){
    try{return JSON.parse(localStorage.getItem('underreported-v6-location')||'null')}catch{return null}
  }

  function findServiceRow(name){
    const root=document.getElementById('admin-live-ops');
    if(!root)return null;
    return [...root.querySelectorAll('div')].find(el=>{
      const first=el.querySelector(':scope > div:nth-child(2) > div:first-child');
      return first?.textContent.trim()===name;
    })||null;
  }

  function paintRow(row,name,state,detail){
    if(!row)return;
    const label=row.querySelector(':scope > div:nth-child(2) > div:first-child');
    const sub=row.querySelector(':scope > div:nth-child(2) > div:nth-child(2)');
    const badge=row.querySelector(':scope > strong');
    const dot=row.querySelector(':scope > span');
    if(label)label.textContent=name;
    if(sub)sub.textContent=detail;
    if(badge){badge.textContent=state.toUpperCase();badge.style.color=stateColor[state]||stateColor.red}
    if(dot){dot.style.background=stateColor[state]||stateColor.red;dot.style.boxShadow=`0 0 0 4px ${state==='green'?'rgba(21,128,61,.10)':state==='yellow'?'rgba(180,83,9,.10)':'rgba(185,28,28,.10)'}`}
  }

  function collectorRow(){
    let row=document.getElementById('cloudflare-collector-row');
    if(row)return row;
    const statusRow=findServiceRow('Status API');
    const parent=statusRow?.parentElement;
    if(!parent)return null;
    row=document.createElement('div');
    row.id='cloudflare-collector-row';
    row.style.cssText='display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:9px;align-items:center;padding:9px 0;border-top:1px solid var(--line)';
    row.innerHTML='<span style="width:9px;height:9px;border-radius:50%;background:#b45309;box-shadow:0 0 0 4px rgba(180,83,9,.10);flex:0 0 auto"></span><div><div style="font-size:.65rem;font-weight:900">Cloudflare Collector</div><div style="font-size:.56rem;color:var(--muted);margin-top:2px">Waiting for first scheduled refresh</div></div><strong style="font-size:.58rem;color:#b45309">YELLOW</strong>';
    statusRow.insertAdjacentElement('afterend',row);
    return row;
  }

  function updateOverallBanner(hasRed,hasYellow){
    const wrap=feed.firstElementChild;
    if(!wrap)return;
    const headings=[...wrap.querySelectorAll('div,strong,h2,h3')];
    const title=headings.find(el=>/^All Systems operational$/i.test(el.textContent.trim())||/^System attention needed$/i.test(el.textContent.trim())||/^Systems degraded$/i.test(el.textContent.trim()));
    if(!title)return;
    if(hasRed)title.textContent='System attention needed';
    else if(hasYellow)title.textContent='Systems operational with warnings';
    else title.textContent='All Systems operational';
  }

  async function refresh(){
    if(!active()||busy)return;
    busy=true;
    try{
      const loc=savedLocation();
      const weatherPath=loc?.lat&&loc?.lon?`/api/weather?lat=${encodeURIComponent(loc.lat)}&lon=${encodeURIComponent(loc.lon)}`:null;
      const [health,weather]=await Promise.all([
        getJson('/healthz'),
        weatherPath?getJson(weatherPath):Promise.resolve({ok:false,waiting:true,ms:0})
      ]);

      const weatherRow=findServiceRow('Open-Meteo Weather')||findServiceRow('Weather Proxy');
      if(weather.waiting)paintRow(weatherRow,'Weather Proxy','yellow','Waiting for saved location');
      else paintRow(weatherRow,'Weather Proxy',weather.ok?'green':'red',weather.ok?`${weather.ms} ms · Cloudflare proxy healthy`:`Unavailable · ${weather.status||weather.error||'request failed'}`);

      const legacy=findServiceRow('GitHub Pages')||findServiceRow('Cloudflare Worker');
      const runtime=health.data?.runtime||'unknown';
      const workerState=health.ok&&runtime==='cloudflare'?'green':health.ok?'yellow':'red';
      const workerDetail=health.ok?`${health.ms} ms · ${runtime} · feed age ${health.data?.ageMinutes??'—'}m`:`Unavailable · ${health.status||health.error||'request failed'}`;
      paintRow(legacy,'Cloudflare Worker',workerState,workerDetail);

      const row=collectorRow();
      const batch=health.data?.batch;
      if(row){
        let state='yellow',detail='Waiting for first scheduled refresh';
        if(batch){
          const errs=Number(health.data?.collectorErrors||0);
          state=health.ok&&errs===0?'green':health.ok?'yellow':'red';
          detail=`batch ${batch.cursor??0}→${batch.nextCursor??0} · ${batch.incomingStories??0} incoming · ${batch.retiredStale??0} stale retired · ${batch.retiredLowView??0} low-view retired · pool ${health.data?.poolStoryCount??'—'}`;
        }
        paintRow(row,'Cloudflare Collector',state,detail);
      }

      const rows=[...document.querySelectorAll('#admin-live-ops > section:first-child > div:last-child > div')];
      const badges=rows.map(r=>r.querySelector(':scope > strong')?.textContent.trim().toLowerCase()).filter(Boolean);
      updateOverallBanner(badges.includes('red'),badges.includes('yellow'));
    }finally{busy=false}
  }

  const observer=new MutationObserver(()=>{if(active())setTimeout(refresh,80)});
  observer.observe(feed,{childList:true,subtree:true});
  tabs.addEventListener('click',e=>{if(e.target.closest('.tab[data-category="admin"]'))setTimeout(refresh,250)},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')setTimeout(refresh,120)});
  setInterval(()=>{if(active())refresh()},30000);
})();
