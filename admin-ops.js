(()=>{
  const feedRoot=document.getElementById('feed');
  if(!feedRoot)return;
  const COLORS={green:'#15803d',yellow:'#b45309',red:'#b91c1c',blue:'#2563eb',purple:'#7c3aed',cyan:'#0891b2',muted:'var(--muted)',text:'var(--text)',line:'var(--line)',surface:'var(--surface)'};
  const LABELS={top:'Top Stories',nfl:'NFL',x:'X',underreported:'Underreported',world:'World',us:'US',presidential:'Presidential',federal:'Federal',legislation:'Legislation',nm:'New Mexico',local:'Local',region:'Region',technology:'Technology',gaming:'Gaming',military:'Military',entertainment:'Entertainment',boxoffice:'Box Office'};
  let busy=false,lastKey='';
  const ageText=ms=>{const m=Math.max(0,Math.round(ms/60000));if(m<60)return`${m}m`;const h=Math.floor(m/60),rm=m%60;return h<24?`${h}h${rm?` ${rm}m`:''}`:`${Math.floor(h/24)}d ${h%24}h`};
  const fmt=n=>Number(n||0).toLocaleString();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pill=(text,color=COLORS.blue,bg='transparent')=>`<span style="display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:999px;border:1px solid color-mix(in srgb,${color} 25%,var(--line));background:${bg==='transparent'?`color-mix(in srgb,${color} 7%,var(--surface))`:bg};color:${color};font-size:.58rem;font-weight:900;white-space:nowrap">${text}</span>`;
  const card=(title,value,sub,color=COLORS.blue,extra='')=>`<div style="background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:13px;box-shadow:0 8px 22px rgba(15,23,42,.07);min-width:0"><div style="font-size:.57rem;font-weight:950;letter-spacing:.08em;color:var(--muted);text-transform:uppercase">${esc(title)}</div><div style="font-size:1.35rem;line-height:1;font-weight:950;margin:7px 0 5px;color:${color}">${esc(value)}</div><div style="font-size:.63rem;line-height:1.35;color:var(--muted)">${esc(sub)}</div>${extra}</div>`;
  const section=(title,sub,html)=>`<section style="display:grid;gap:9px"><div><div style="font-size:.7rem;font-weight:950;color:var(--text)">${title}</div>${sub?`<div style="font-size:.61rem;color:var(--muted);margin-top:2px">${sub}</div>`:''}</div>${html}</section>`;
  async function j(path){const r=await fetch(`${path}${path.includes('?')?'&':'?'}ts=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(`${path} ${r.status}`);return r.json()}
  function flatten(feed){const rows=[];for(const [cat,arr] of Object.entries(feed?.stories||{}))for(const s of arr||[])rows.push({...s,category:cat});return rows}
  function publishedMs(s){const v=Date.parse(s.published_at||s.publishedAt||s.date||'');return Number.isFinite(v)?v:0}
  async function deployment(){try{const r=await fetch('https://api.github.com/repos/battleatom/News/actions/workflows/pages/pages-build-deployment/runs?per_page=1',{headers:{Accept:'application/vnd.github+json'},cache:'no-store'});if(!r.ok)throw new Error(String(r.status));const d=await r.json(),run=d.workflow_runs?.[0];if(!run)return null;return{status:run.status,conclusion:run.conclusion,sha:String(run.head_sha||'').slice(0,7),created:run.created_at}}catch{return null}}
  async function localHealth(){const checks=[['Feed','feed.json'],['NFL','nfl.json'],['Markets','markets.json'],['Box Office','boxoffice.json']];return Promise.all(checks.map(async([name,path])=>{const t=performance.now();try{await j(path);return{name,ok:true,ms:Math.round(performance.now()-t)}}catch(e){return{name,ok:false,ms:Math.round(performance.now()-t),error:String(e.message||e)}}))}
  async function build(){
    const [status,feed,dep,health]=await Promise.all([j('status.json'),j('feed.json'),deployment(),localHealth()]);
    const all=flatten(feed),now=Date.now();
    const newestByCat=[];
    for(const [cat,arr] of Object.entries(feed?.stories||{})){
      const times=(arr||[]).map(publishedMs).filter(Boolean).sort((a,b)=>b-a),newest=times[0]||0;
      newestByCat.push({cat,count:(arr||[]).length,newest,age:newest?now-newest:Infinity});
    }
    newestByCat.sort((a,b)=>b.age-a.age);
    const last1=all.filter(s=>publishedMs(s)&&now-publishedMs(s)<=3600000).length,last6=all.filter(s=>publishedMs(s)&&now-publishedMs(s)<=21600000).length,last24=all.filter(s=>publishedMs(s)&&now-publishedMs(s)<=86400000).length;
    const sourceRows=status.sourceStatuses||[],zeroSources=sourceRows.filter(s=>Number(s.storyCount||0)===0),failed=sourceRows.filter(s=>s.status!=='live'||s.error),collectorErrors=status.collectorErrors||[];
    const feedback=status.feedbackPoolCounts||{},feedbackTotal=Number(feedback.D||0)+Number(feedback.NR||0)+Number(feedback.NW||0);
    const publishedCount=Number(status.storyCount||all.length),poolCount=Number(status.poolStoryCount||publishedCount),suppressed=Math.max(0,poolCount-publishedCount),duplicateRate=poolCount?suppressed/poolCount:0;
    const stale=newestByCat.filter(x=>x.age>6*3600000&&x.cat!=='boxoffice');
    const attention=[];
    for(const e of collectorErrors.slice(0,4))attention.push({color:COLORS.red,text:typeof e==='string'?e:(e.error||e.message||'Collector error')});
    for(const s of failed.slice(0,4))attention.push({color:COLORS.red,text:`${s.name||s.id} · ${s.error||'source unavailable'}`});
    for(const c of stale.slice(0,4))attention.push({color:COLORS.yellow,text:`${LABELS[c.cat]||c.cat} · newest story ${ageText(c.age)} old`});
    for(const s of zeroSources.slice(0,3))attention.push({color:COLORS.yellow,text:`${s.name||s.id} · 0 stories returned`});
    if(dep&&dep.status!=='completed')attention.push({color:COLORS.blue,text:`Pages deployment ${dep.status} · ${dep.sha}`});
    if(dep&&dep.status==='completed'&&dep.conclusion!=='success')attention.push({color:COLORS.red,text:`Pages deployment ${dep.conclusion||'failed'} · ${dep.sha}`});
    const attHtml=attention.length?`<div style="display:grid;gap:6px">${attention.slice(0,8).map(a=>`<div style="display:flex;gap:8px;align-items:flex-start;padding:9px 10px;border-radius:12px;border:1px solid color-mix(in srgb,${a.color} 22%,var(--line));background:color-mix(in srgb,${a.color} 6%,var(--surface));font-size:.65rem;line-height:1.35"><span style="width:8px;height:8px;border-radius:50%;background:${a.color};margin-top:3px;flex:0 0 auto"></span><span>${esc(a.text)}</span></div>`).join('')}</div>`:`<div style="padding:10px 11px;border-radius:12px;background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.18);color:#15803d;font-size:.66rem;font-weight:850">✓ Nothing needs attention right now.</div>`;
    const freshness=`<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px">${newestByCat.filter(x=>x.cat!=='boxoffice').map(x=>{const color=x.age<=2*3600000?COLORS.green:x.age<=6*3600000?COLORS.blue:x.age<=12*3600000?COLORS.yellow:COLORS.red;return`<div style="padding:10px;border:1px solid var(--line);border-radius:13px;background:var(--surface)"><div style="display:flex;align-items:center;justify-content:space-between;gap:6px"><strong style="font-size:.63rem">${esc(LABELS[x.cat]||x.cat)}</strong><span style="width:8px;height:8px;border-radius:50%;background:${color}"></span></div><div style="font-size:.9rem;font-weight:950;color:${color};margin-top:5px">${Number.isFinite(x.age)?ageText(x.age):'—'}</div><div style="font-size:.56rem;color:var(--muted);margin-top:2px">${fmt(x.count)} stories · newest</div></div>`}).join('')}</div>`;
    const healthHtml=`<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px">${health.map(h=>`<div style="padding:10px;border-radius:13px;border:1px solid ${h.ok?'rgba(34,197,94,.18)':'rgba(239,68,68,.20)'};background:${h.ok?'rgba(34,197,94,.05)':'rgba(239,68,68,.05)'}"><div style="display:flex;align-items:center;gap:6px;font-size:.64rem;font-weight:900"><span style="width:8px;height:8px;border-radius:50%;background:${h.ok?COLORS.green:COLORS.red}"></span>${esc(h.name)}</div><div style="font-size:.57rem;color:var(--muted);margin-top:4px">${h.ok?`${h.ms} ms response`:esc(h.error||'Unavailable')}</div></div>`).join('')}</div>`;
    const deployColor=!dep?COLORS.muted:dep.status==='completed'&&dep.conclusion==='success'?COLORS.green:dep.status==='in_progress'?COLORS.blue:COLORS.red;
    const html=`<div id="admin-live-ops" style="display:grid;gap:15px;margin-top:4px">
      ${section('Needs Attention','Live warnings only; this stays quiet when the system is healthy.',attHtml)}
      ${section('Live Activity','Current publication and suppression activity.',`<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">${card('Last hour',last1,'new stories',COLORS.green)}${card('Last 6 hours',last6,'new stories',COLORS.blue)}${card('Last 24 hours',last24,'new stories',COLORS.purple)}</div><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">${card('Suppressed',suppressed,`${(duplicateRate*100).toFixed(1)}% of pool`,duplicateRate>.2?COLORS.yellow:COLORS.cyan)}${card('Feedback',feedbackTotal,`D ${fmt(feedback.D)} · NR ${fmt(feedback.NR)} · NW ${fmt(feedback.NW)}`,COLORS.yellow)}${card('Reserve',status.reserveStoryCount||0,'standby stories',COLORS.cyan)}</div>`)}
      ${section('Content Freshness','Age of the newest published story in each category.',freshness)}
      ${section('Service Health','Live response checks from the browser.',healthHtml)}
      ${section('Deployment','GitHub Pages production state.',`<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 12px;border-radius:13px;border:1px solid var(--line);background:var(--surface)"><div><div style="font-size:.67rem;font-weight:900">GitHub Pages</div><div style="font-size:.58rem;color:var(--muted);margin-top:3px">${dep?`${dep.sha}${dep.created?` · ${new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(new Date(dep.created))}`:''}`:'Status unavailable'}</div></div>${pill(dep?(dep.status==='completed'?(dep.conclusion||'completed'):dep.status):'unknown',deployColor)}</div>`)}
      ${section('Source Performance','Lowest-yield and unavailable sources surface first.',`<div style="display:grid;gap:5px">${[...sourceRows].sort((a,b)=>{const ae=a.status!=='live'||a.error?1:0,be=b.status!=='live'||b.error?1:0;return be-ae||Number(a.storyCount||0)-Number(b.storyCount||0)}).slice(0,12).map(s=>{const bad=s.status!=='live'||s.error,zero=Number(s.storyCount||0)===0,color=bad?COLORS.red:zero?COLORS.yellow:COLORS.green;return`<div style="display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:center;padding:7px 0;border-top:1px solid var(--line)"><span style="width:8px;height:8px;border-radius:50%;background:${color}"></span><div style="min-width:0"><div style="font-size:.63rem;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(s.name||s.id)}</div><div style="font-size:.55rem;color:var(--muted)">${esc(LABELS[s.category]||s.category||'source')}${s.error?` · ${esc(s.error)}`:''}</div></div><strong style="font-size:.6rem;color:${color}">${fmt(s.storyCount)}</strong></div>`}).join('')}</div>`)}
    </div>`;
    return{html,key:`${status.generatedAt}|${dep?.sha||''}|${feedbackTotal}`};
  }
  async function enhance(){
    if(busy||document.body.dataset.activeTab!=='admin')return;
    busy=true;
    try{
      const result=await build();
      let host=document.getElementById('admin-live-ops');
      if(result.key===lastKey&&host)return;
      lastKey=result.key;
      host?.remove();
      const wrap=feedRoot.firstElementChild;
      if(wrap)wrap.insertAdjacentHTML('beforeend',result.html);
    }catch(e){console.warn('Admin live ops unavailable',e)}finally{busy=false}
  }
  new MutationObserver(()=>{if(document.body.dataset.activeTab==='admin')setTimeout(enhance,40)}).observe(feedRoot,{childList:true,subtree:false});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)enhance()});
  setInterval(enhance,30000);
})();