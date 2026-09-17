(()=>{
  const tabs=document.getElementById('tabs'),feed=document.getElementById('feed');
  if(!tabs||!feed)return;
  const escXml=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[m]));
  const active=()=>!!tabs.querySelector('.tab[data-category="admin"][aria-selected="true"]');
  const download=(name,text,type)=>{const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  async function snapshot(){
    const [status,feedData]=await Promise.all([
      fetch(`/status.json?export=${Date.now()}`,{cache:'no-store'}).then(r=>r.json()),
      fetch(`/feed.json?export=${Date.now()}`,{cache:'no-store'}).then(r=>r.json())
    ]);
    const runtimeRows=[...document.querySelectorAll('#admin-runtime-files > div:last-child > div')].map(row=>({
      path:row.querySelector('div>div:first-child')?.textContent?.trim()||'',
      detail:row.querySelector('div>div:nth-child(2)')?.textContent?.trim()||'',
      state:row.querySelector('strong')?.textContent?.trim()||''
    }));
    return{
      exportedAt:new Date().toISOString(),generatedAt:status.generatedAt||status.generated_at||'',storyCount:status.storyCount??'',poolStoryCount:status.poolStoryCount??'',reserveStoryCount:status.reserveStoryCount??'',sourceCount:status.sourceCount??'',healthySourceCount:status.healthySourceCount??'',warningSourceCount:status.warningSourceCount??'',deadSourceCount:status.deadSourceCount??'',categoryCounts:status.categoryCounts||{},reserveCounts:status.reserveCounts||{},collectorErrors:Array.isArray(status.collectorErrors)?status.collectorErrors:[],sourceStatuses:Array.isArray(status.sourceStatuses)?status.sourceStatuses:[],cloudflareBatch:status.cloudflareBatch||{},runtimeRows,feedCategories:Object.fromEntries(Object.entries(feedData?.stories||{}).map(([k,v])=>[k,Array.isArray(v)?v.length:0])),feedReserves:Object.fromEntries(Object.entries(feedData?.reserves||{}).map(([k,v])=>[k,Array.isArray(v)?v.length:0]))
    };
  }
  function toXml(s){
    const entries=o=>Object.entries(o||{}).map(([k,v])=>`<entry key="${escXml(k)}">${escXml(typeof v==='object'?JSON.stringify(v):v)}</entry>`).join('');
    const sources=s.sourceStatuses.map(x=>`<source><id>${escXml(x.id)}</id><name>${escXml(x.name)}</name><category>${escXml(x.category)}</category><status>${escXml(x.status)}</status><storyCount>${escXml(x.storyCount)}</storyCount><error>${escXml(x.error)}</error><consecutiveFailures>${escXml(x.consecutiveFailures)}</consecutiveFailures><lastChecked>${escXml(x.lastChecked)}</lastChecked><lastSuccess>${escXml(x.lastSuccess)}</lastSuccess><lastSuccessStoryCount>${escXml(x.lastSuccessStoryCount)}</lastSuccessStoryCount><attempts>${escXml(x.attempts)}</attempts></source>`).join('');
    const collectors=s.collectorErrors.map(e=>`<error>${escXml(typeof e==='string'?e:JSON.stringify(e))}</error>`).join('');
    const runtime=s.runtimeRows.map(r=>`<file><path>${escXml(r.path)}</path><state>${escXml(r.state)}</state><detail>${escXml(r.detail)}</detail></file>`).join('');
    return `<?xml version="1.0" encoding="UTF-8"?><adminDiagnostics><exportedAt>${escXml(s.exportedAt)}</exportedAt><generatedAt>${escXml(s.generatedAt)}</generatedAt><summary><storyCount>${escXml(s.storyCount)}</storyCount><poolStoryCount>${escXml(s.poolStoryCount)}</poolStoryCount><reserveStoryCount>${escXml(s.reserveStoryCount)}</reserveStoryCount><sourceCount>${escXml(s.sourceCount)}</sourceCount><healthySourceCount>${escXml(s.healthySourceCount)}</healthySourceCount><warningSourceCount>${escXml(s.warningSourceCount)}</warningSourceCount><deadSourceCount>${escXml(s.deadSourceCount)}</deadSourceCount></summary><cloudflareBatch>${entries(s.cloudflareBatch)}</cloudflareBatch><categoryCounts>${entries(s.categoryCounts)}</categoryCounts><reserveCounts>${entries(s.reserveCounts)}</reserveCounts><collectorErrors>${collectors}</collectorErrors><sourceStatuses>${sources}</sourceStatuses><runtimeFiles>${runtime}</runtimeFiles><feedCategories>${entries(s.feedCategories)}</feedCategories><feedReserves>${entries(s.feedReserves)}</feedReserves></adminDiagnostics>`;
  }
  async function run(button){const old=button.textContent;button.disabled=true;button.textContent='Preparing…';try{const s=await snapshot(),stamp=new Date().toISOString().replace(/[:.]/g,'-');download(`admin-diagnostics-${stamp}.xml`,toXml(s),'application/xml;charset=utf-8')}catch(e){console.error(e);alert('Could not export diagnostics: '+(e?.message||e))}finally{button.disabled=false;button.textContent=old}}
  function ensure(){
    if(!active()||document.getElementById('admin-export-tools'))return;
    const root=document.getElementById('admin-live-ops');if(!root)return;
    const box=document.createElement('section');box.id='admin-export-tools';box.style.cssText='display:flex;gap:10px;flex-wrap:wrap;align-items:center;padding:10px 0';
    box.innerHTML='<strong style="font-size:.7rem">Export diagnostics</strong><button type="button" data-export="xml" style="appearance:none;border:1px solid var(--line);border-radius:999px;padding:8px 14px;background:var(--surface,transparent);color:inherit;font:inherit;font-size:.62rem;font-weight:900;cursor:pointer">Export XML</button><span style="font-size:.56rem;color:var(--muted)">Includes source health, retry history, errors, pool/reserve counts, and runtime checks.</span>';
    root.prepend(box);box.addEventListener('click',e=>{const b=e.target.closest('button[data-export="xml"]');if(b)run(b)});
  }
  const schedule=()=>{if(active())setTimeout(ensure,80)};
  tabs.addEventListener('click',e=>{if(e.target.closest('.tab[data-category="admin"]'))setTimeout(ensure,350)},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')schedule()});
  document.addEventListener('v6:adminopsrender',schedule);
  new MutationObserver(schedule).observe(feed,{childList:true,subtree:true});
  setTimeout(ensure,500);
})();