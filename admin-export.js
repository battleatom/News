(()=>{
  const tabs=document.getElementById('tabs'),feed=document.getElementById('feed');
  if(!tabs||!feed)return;
  const escCsv=v=>`"${String(v??'').replace(/"/g,'""')}"`;
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
      exportedAt:new Date().toISOString(),
      generatedAt:status.generatedAt||status.generated_at||'',
      storyCount:status.storyCount??'',
      poolStoryCount:status.poolStoryCount??'',
      reserveStoryCount:status.reserveStoryCount??'',
      sourceCount:status.sourceCount??'',
      healthySourceCount:status.healthySourceCount??'',
      categoryCounts:status.categoryCounts||{},
      reserveCounts:status.reserveCounts||{},
      collectorErrors:Array.isArray(status.collectorErrors)?status.collectorErrors:[],
      sourceStatuses:Array.isArray(status.sourceStatuses)?status.sourceStatuses:[],
      runtimeRows,
      feedCategories:Object.fromEntries(Object.entries(feedData?.stories||{}).map(([k,v])=>[k,Array.isArray(v)?v.length:0])),
      feedReserves:Object.fromEntries(Object.entries(feedData?.reserves||{}).map(([k,v])=>[k,Array.isArray(v)?v.length:0]))
    };
  }
  function toCsv(s){
    const rows=[['section','id','name','category','status','storyCount','error','detail']];
    rows.push(['summary','storyCount','','','',s.storyCount,'','']);
    rows.push(['summary','poolStoryCount','','','',s.poolStoryCount,'','']);
    rows.push(['summary','reserveStoryCount','','','',s.reserveStoryCount,'','']);
    rows.push(['summary','sourceCount','','','',s.sourceCount,'','']);
    rows.push(['summary','healthySourceCount','','','',s.healthySourceCount,'','']);
    for(const [k,v] of Object.entries(s.categoryCounts))rows.push(['category',k,'',k,'',v,'','visible']);
    for(const [k,v] of Object.entries(s.reserveCounts))rows.push(['reserve',k,'',k,'',v,'','reserve']);
    for(const x of s.sourceStatuses)rows.push(['source',x.id||'',x.name||'',x.category||'',x.status||'',x.storyCount??'',x.error||'','']);
    for(const e of s.collectorErrors)rows.push(['collector','','','','','','',typeof e==='string'?e:JSON.stringify(e)]);
    for(const r of s.runtimeRows)rows.push(['runtime',r.path,'','',''+r.state,'','',r.detail]);
    return rows.map(r=>r.map(escCsv).join(',')).join('\n');
  }
  function toXml(s){
    const entries=o=>Object.entries(o||{}).map(([k,v])=>`<entry key="${escXml(k)}">${escXml(v)}</entry>`).join('');
    const sources=s.sourceStatuses.map(x=>`<source><id>${escXml(x.id)}</id><name>${escXml(x.name)}</name><category>${escXml(x.category)}</category><status>${escXml(x.status)}</status><storyCount>${escXml(x.storyCount)}</storyCount><error>${escXml(x.error)}</error></source>`).join('');
    const collectors=s.collectorErrors.map(e=>`<error>${escXml(typeof e==='string'?e:JSON.stringify(e))}</error>`).join('');
    const runtime=s.runtimeRows.map(r=>`<file><path>${escXml(r.path)}</path><state>${escXml(r.state)}</state><detail>${escXml(r.detail)}</detail></file>`).join('');
    return `<?xml version="1.0" encoding="UTF-8"?><adminDiagnostics><exportedAt>${escXml(s.exportedAt)}</exportedAt><generatedAt>${escXml(s.generatedAt)}</generatedAt><summary><storyCount>${escXml(s.storyCount)}</storyCount><poolStoryCount>${escXml(s.poolStoryCount)}</poolStoryCount><reserveStoryCount>${escXml(s.reserveStoryCount)}</reserveStoryCount><sourceCount>${escXml(s.sourceCount)}</sourceCount><healthySourceCount>${escXml(s.healthySourceCount)}</healthySourceCount></summary><categoryCounts>${entries(s.categoryCounts)}</categoryCounts><reserveCounts>${entries(s.reserveCounts)}</reserveCounts><collectorErrors>${collectors}</collectorErrors><sourceStatuses>${sources}</sourceStatuses><runtimeFiles>${runtime}</runtimeFiles><feedCategories>${entries(s.feedCategories)}</feedCategories><feedReserves>${entries(s.feedReserves)}</feedReserves></adminDiagnostics>`;
  }
  async function run(format,button){
    const old=button.textContent;button.disabled=true;button.textContent='Preparing…';
    try{const s=await snapshot(),stamp=new Date().toISOString().replace(/[:.]/g,'-');if(format==='csv')download(`admin-diagnostics-${stamp}.csv`,toCsv(s),'text/csv;charset=utf-8');else download(`admin-diagnostics-${stamp}.xml`,toXml(s),'application/xml;charset=utf-8')}catch(e){console.error(e);alert('Could not export diagnostics: '+(e?.message||e))}finally{button.disabled=false;button.textContent=old}
  }
  function ensure(){
    if(!active())return;
    const wrap=feed.firstElementChild;if(!wrap||document.getElementById('admin-export-tools'))return;
    const box=document.createElement('section');box.id='admin-export-tools';box.style.cssText='display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:10px 0';
    box.innerHTML='<strong style="font-size:.7rem">Export diagnostics</strong><button type="button" data-export="csv" class="text-button">Export CSV</button><button type="button" data-export="xml" class="text-button">Export XML</button><span style="font-size:.56rem;color:var(--muted)">Includes source health, errors, pool/reserve counts, and runtime checks.</span>';
    wrap.prepend(box);
    box.addEventListener('click',e=>{const b=e.target.closest('button[data-export]');if(b)run(b.dataset.export,b)});
  }
  tabs.addEventListener('click',e=>{if(e.target.closest('.tab[data-category="admin"]'))setTimeout(ensure,400)},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')setTimeout(ensure,250)});
  new MutationObserver(()=>{if(active())setTimeout(ensure,0)}).observe(feed,{childList:true,subtree:false});
  setTimeout(ensure,500);
})();