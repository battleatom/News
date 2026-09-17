(()=>{
  const tabs=document.getElementById('tabs'),feed=document.getElementById('feed');
  if(!tabs||!feed)return;
  const FILES=[
    ['script','app.js'],['script','store.js'],['script','renderers.js'],['script','location.js'],['script','feedback.js'],['script','weather.js'],['script','nfl-cloudflare-proxy.js'],['script','story-sanitize.js'],['script','infinite-scroll.js'],['script','story-position.js'],['script','status-ux.js'],['script','tab-ux.js'],['script','admin-ops.js'],['script','admin-layout.js'],['script','admin-refresh.js'],['script','admin-pool.js'],['script','admin-cloudflare.js'],['script','admin-runtime-files.js'],
    ['json','feed.json'],['json','status.json'],['json','nfl.json'],['json','markets.json'],['json','boxoffice.json'],['json','sources.json'],['json','sources-extra.json']
  ];
  const LEGACY=[['supabase.co','legacy Supabase reference'],['vercel.app','legacy Vercel reference'],['github.io','legacy GitHub Pages reference'],['raw.githubusercontent.com','raw GitHub runtime reference']];
  let busy=false;
  const active=()=>!!tabs.querySelector('.tab[data-category="admin"][aria-selected="true"]');
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  function duplicateCount(path){return [...document.scripts].filter(s=>{try{return new URL(s.src,location.href).pathname.endsWith('/'+path)||new URL(s.src,location.href).pathname===('/'+path)}catch{return false}}).length}
  async function check(kind,path){
    const started=performance.now();
    try{
      const r=await fetch(`/${path}?diag=${Date.now()}`,{cache:'no-store'}),ms=Math.round(performance.now()-started),fallback=r.headers.get('X-Underreported-Fallback')==='1';
      if(!r.ok)return{kind,path,state:'red',label:'NOT WORKING',detail:`HTTP ${r.status} · ${ms} ms`};
      const text=await r.text();
      if(!text.trim())return{kind,path,state:'red',label:'NOT WORKING',detail:`empty response · ${ms} ms`};
      if(kind==='script'){
        const ct=String(r.headers.get('content-type')||'').toLowerCase();
        if(ct.includes('text/html')||/^\s*<!doctype html/i.test(text))return{kind,path,state:'red',label:'NOT WORKING',detail:`HTML returned instead of JavaScript · ${ms} ms`};
        const legacy=LEGACY.find(([needle])=>text.includes(needle));
        if(legacy)return{kind,path,state:'yellow',label:'CONFLICT',detail:`${legacy[1]} · ${ms} ms`};
        const dup=duplicateCount(path);if(dup>1)return{kind,path,state:'yellow',label:'CONFLICT',detail:`loaded ${dup} times in page · ${ms} ms`};
        return{kind,path,state:'green',label:'WORKING',detail:`served by Cloudflare · ${ms} ms`};
      }
      let data;try{data=JSON.parse(text)}catch{return{kind,path,state:'red',label:'NOT WORKING',detail:`invalid JSON · ${ms} ms`}};
      if(fallback)return{kind,path,state:'yellow',label:'CONFLICT',detail:`Cloudflare live handler fell back to bundled snapshot · ${ms} ms`};
      if(['feed.json','status.json','nfl.json','markets.json','boxoffice.json'].includes(path)&&data?.cloudflareRuntime!==true){
        return{kind,path,state:'yellow',label:'CONFLICT',detail:`valid JSON but not marked Cloudflare runtime · ${ms} ms`};
      }
      return{kind,path,state:'green',label:'WORKING',detail:`valid JSON · ${ms} ms`};
    }catch(error){return{kind,path,state:'red',label:'NOT WORKING',detail:String(error?.message||error)}}
  }
  function dot(state){const c=state==='green'?'#15803d':state==='yellow'?'#b45309':'#b91c1c';return`<span style="width:9px;height:9px;border-radius:50%;background:${c};box-shadow:0 0 0 4px color-mix(in srgb,${c} 12%,transparent);flex:0 0 auto"></span>`}
  function row(x){const c=x.state==='green'?'#15803d':x.state==='yellow'?'#b45309':'#b91c1c';return`<div style="display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:9px;align-items:center;padding:9px 0;border-top:1px solid var(--line)">${dot(x.state)}<div style="min-width:0"><div style="font-size:.65rem;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(x.path)}</div><div style="font-size:.56rem;color:var(--muted);margin-top:2px">${esc(x.kind.toUpperCase())} · ${esc(x.detail)}</div></div><strong style="font-size:.56rem;color:${c};white-space:nowrap">${esc(x.label)}</strong></div>`}
  async function render(){
    if(!active()||busy)return;busy=true;
    try{
      const results=await Promise.all(FILES.map(([kind,path])=>check(kind,path)));
      const ok=results.filter(x=>x.state==='green').length,conflicts=results.filter(x=>x.state==='yellow').length,bad=results.filter(x=>x.state==='red').length;
      const root=document.getElementById('admin-live-ops')||feed.firstElementChild;if(!root)return;
      let section=document.getElementById('admin-runtime-files');if(!section){section=document.createElement('section');section.id='admin-runtime-files';section.style.cssText='display:grid;gap:8px;margin-top:2px';root.appendChild(section)}
      section.innerHTML=`<div><div style="font-size:.7rem;font-weight:950">Runtime Files</div><div style="font-size:.6rem;color:var(--muted);margin-top:2px">Checks the deployed Cloudflare scripts and JSON files. Conflict means a legacy dependency, duplicate load, non-Cloudflare runtime response, or fallback snapshot.</div></div><div style="display:flex;gap:7px;flex-wrap:wrap;font-size:.57rem;font-weight:900"><span style="color:#15803d">${ok} working</span><span style="color:#b45309">${conflicts} conflicts</span><span style="color:#b91c1c">${bad} not working</span></div><div>${results.map(row).join('')}</div>`;
    }finally{busy=false}
  }
  tabs.addEventListener('click',e=>{if(e.target.closest('.tab[data-category="admin"]'))setTimeout(render,500)},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')setTimeout(render,300)});
  setInterval(()=>{if(active())render()},60000);
})();