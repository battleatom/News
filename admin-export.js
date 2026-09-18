(()=>{
  const escXml=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[m]));
  let cached=null,cachedAt=0,priming=false;
  const download=(name,text,type)=>{const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.style.display='none';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500)};
  async function snapshot(){
    const [statusResp,feedResp]=await Promise.all([
      fetch('/status.json?export='+Date.now(),{cache:'no-store'}),
      fetch('/feed.json?export='+Date.now(),{cache:'no-store'})
    ]);
    if(!statusResp.ok)throw new Error('status.json '+statusResp.status);
    if(!feedResp.ok)throw new Error('feed.json '+feedResp.status);
    const status=await statusResp.json(),feedData=await feedResp.json();
    const runtimeRows=[...document.querySelectorAll('#admin-runtime-files > div:last-child > div')].map(row=>({path:row.querySelector('div>div:first-child')?.textContent?.trim()||'',detail:row.querySelector('div>div:nth-child(2)')?.textContent?.trim()||'',state:row.querySelector('strong')?.textContent?.trim()||''}));
    return{exportedAt:new Date().toISOString(),generatedAt:status.generatedAt||status.generated_at||'',storyCount:status.storyCount??'',poolStoryCount:status.poolStoryCount??'',reserveStoryCount:status.reserveStoryCount??'',sourceCount:status.sourceCount??'',healthySourceCount:status.healthySourceCount??'',warningSourceCount:status.warningSourceCount??'',deadSourceCount:status.deadSourceCount??'',categoryCounts:status.categoryCounts||{},reserveCounts:status.reserveCounts||{},collectorErrors:Array.isArray(status.collectorErrors)?status.collectorErrors:[],sourceStatuses:Array.isArray(status.sourceStatuses)?status.sourceStatuses:[],cloudflareBatch:status.cloudflareBatch||{},runtimeRows,feedCategories:Object.fromEntries(Object.entries(feedData?.stories||{}).map(([k,v])=>[k,Array.isArray(v)?v.length:0])),feedReserves:Object.fromEntries(Object.entries(feedData?.reserves||{}).map(([k,v])=>[k,Array.isArray(v)?v.length:0]))};
  }
  function toXml(s){
    const entries=o=>Object.entries(o||{}).map(([k,v])=>`<entry key="${escXml(k)}">${escXml(typeof v==='object'?JSON.stringify(v):v)}</entry>`).join('');
    const sources=s.sourceStatuses.map(x=>`<source><id>${escXml(x.id)}</id><name>${escXml(x.name)}</name><category>${escXml(x.category)}</category><status>${escXml(x.status)}</status><storyCount>${escXml(x.storyCount)}</storyCount><error>${escXml(x.error)}</error><consecutiveFailures>${escXml(x.consecutiveFailures)}</consecutiveFailures><lastChecked>${escXml(x.lastChecked)}</lastChecked><lastSuccess>${escXml(x.lastSuccess)}</lastSuccess><lastSuccessStoryCount>${escXml(x.lastSuccessStoryCount)}</lastSuccessStoryCount><attempts>${escXml(x.attempts)}</attempts></source>`).join('');
    const collectors=s.collectorErrors.map(e=>`<error>${escXml(typeof e==='string'?e:JSON.stringify(e))}</error>`).join('');
    const runtime=s.runtimeRows.map(r=>`<file><path>${escXml(r.path)}</path><state>${escXml(r.state)}</state><detail>${escXml(r.detail)}</detail></file>`).join('');
    return `<?xml version="1.0" encoding="UTF-8"?><adminDiagnostics><exportedAt>${escXml(s.exportedAt)}</exportedAt><generatedAt>${escXml(s.generatedAt)}</generatedAt><summary><storyCount>${escXml(s.storyCount)}</storyCount><poolStoryCount>${escXml(s.poolStoryCount)}</poolStoryCount><reserveStoryCount>${escXml(s.reserveStoryCount)}</reserveStoryCount><sourceCount>${escXml(s.sourceCount)}</sourceCount><healthySourceCount>${escXml(s.healthySourceCount)}</healthySourceCount><warningSourceCount>${escXml(s.warningSourceCount)}</warningSourceCount><deadSourceCount>${escXml(s.deadSourceCount)}</deadSourceCount></summary><cloudflareBatch>${entries(s.cloudflareBatch)}</cloudflareBatch><categoryCounts>${entries(s.categoryCounts)}</categoryCounts><reserveCounts>${entries(s.reserveCounts)}</reserveCounts><collectorErrors>${collectors}</collectorErrors><sourceStatuses>${sources}</sourceStatuses><runtimeFiles>${runtime}</runtimeFiles><feedCategories>${entries(s.feedCategories)}</feedCategories><feedReserves>${entries(s.feedReserves)}</feedReserves></adminDiagnostics>`;
  }
  async function prime(force=false){if(priming)return;if(!force&&cached&&Date.now()-cachedAt<30000)return;priming=true;try{cached=await snapshot();cachedAt=Date.now()}catch(e){console.warn('Diagnostics preload failed',e)}finally{priming=false}}
  function saveCached(button){
    if(!cached)return false;
    const stamp=new Date().toISOString().replace(/[:.]/g,'-');
    download('admin-diagnostics-'+stamp+'.xml',toXml({...cached,exportedAt:new Date().toISOString()}),'application/xml;charset=utf-8');
    button.textContent='Exported ✓';setTimeout(()=>button.textContent='Export XML',1200);
    prime(true);
    return true;
  }
  async function run(button){
    if(saveCached(button))return;
    button.disabled=true;button.textContent='Preparing…';
    try{
      await prime(true);
      if(!saveCached(button))throw new Error('diagnostic snapshot unavailable');
    }catch(e){
      console.error(e);
      alert('Could not export diagnostics: '+(e?.message||e));
      button.textContent='Export XML';
    }finally{button.disabled=false}
  }
  document.addEventListener('click',e=>{const b=e.target.closest('#admin-export-xml-inline,[data-export="xml"]');if(b)run(b)},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')setTimeout(()=>prime(true),150)});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)prime(false)});
  setInterval(()=>prime(false),30000);
  setTimeout(()=>prime(true),500);
})();