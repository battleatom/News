(function(){
  'use strict';
  if(window.__entertainmentV4)return;
  const KEY='entertainment', LABEL='🎭 Entertainment', ACCENT='#be185d';
  const MODE_KEY='underreported-entertainment-mode';
  const DIRTY_UI_ENABLED=false;

  const text=(item,tag)=>item.querySelector(tag)?.textContent?.trim()||'';
  const safe=v=>typeof esc==='function'?esc(v):String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function safeImage(v){try{const u=new URL(v,location.href);return /^https?:$/.test(u.protocol)?u.href:''}catch(e){return ''}}

  function ensureTab(){
    if(!Array.isArray(window.CANONICAL_SECTIONS)&&typeof CANONICAL_SECTIONS==='undefined')return false;
    const list=typeof CANONICAL_SECTIONS!=='undefined'?CANONICAL_SECTIONS:window.CANONICAL_SECTIONS;
    if(!list.some(x=>x[0]===KEY)){
      const under=list.findIndex(x=>x[0]==='underreported');
      list.splice(under>=0?under+1:4,0,[KEY,LABEL,ACCENT]);
    }
    if(typeof sections!=='undefined')sections=list;
    return true;
  }

  function currentMode(){
    if(!DIRTY_UI_ENABLED)return 'clean';
    try{
      const m=new URL(location.href).searchParams.get('entmode');
      if(m==='clean'||m==='dirty'){localStorage.setItem(MODE_KEY,m);return m}
    }catch(e){}
    return localStorage.getItem(MODE_KEY)==='clean'?'clean':'dirty';
  }

  function modeItems(items){
    const mode=currentMode();
    return items.filter(item=>{
      if(text(item,'category')!==KEY)return false;
      const safety=(text(item,'entertainmentSafety')||'clean').toLowerCase();
      return mode==='dirty'?safety==='dirty':safety==='clean';
    });
  }

  function switchMode(mode){
    if(!DIRTY_UI_ENABLED)return;
    const next=mode==='dirty'?'clean':'dirty';
    try{localStorage.setItem(MODE_KEY,next)}catch(e){}
    try{if(typeof loadCounts!=='undefined')loadCounts[KEY]=typeof STORIES_PER_PAGE!=='undefined'?STORIES_PER_PAGE:10}catch(e){}
    const u=new URL(location.href);u.searchParams.set('entmode',next);u.searchParams.set('entv',Date.now());location.href=u.toString();
  }

  function renderEntertainment(items){
    const mode=currentMode(), ordered=modeItems(items);
    const data=typeof paginatedNewsItems==='function'?paginatedNewsItems(ordered):{available:ordered,visible:ordered,count:ordered.length};
    const root=document.getElementById('news-feed');if(!root)return;root.innerHTML='';
    const sec=document.createElement('section');sec.className='section entertainment-section';sec.style.setProperty('--accent',ACCENT);
    const head=document.createElement('div');head.className='section-header ent-section-header';
    head.innerHTML=`<h2>${LABEL}</h2><span class="count">Showing ${data.count} of ${data.available.length} stories</span>`;
    sec.appendChild(head);

    const intro=document.createElement('div');intro.className='x-issues-intro';
    intro.textContent='Major entertainment, careers, awards, family/baby news, marriages and philanthropy. Ranked by importance first, then recency.';
    sec.appendChild(intro);

    const body=document.createElement('div');body.className='section-body';
    if(!data.visible.length)body.innerHTML='<div class="empty">No verified entertainment stories are available right now.</div>';
    data.visible.forEach((item,i)=>{
      const ar=document.createElement('article');ar.className='news-item entertainment-item';
      const title=text(item,'title')||'Untitled', link=text(item,'link')||'#', desc=text(item,'description'), why=text(item,'whyMatters');
      const date=text(item,'pubDate'), source=text(item,'source'), image=safeImage(text(item,'imageUrl'));
      const label=text(item,'entertainmentLabel')||'ENTERTAINMENT', tier=text(item,'entertainmentTier');
      const under=[...item.querySelectorAll('underreportedLinks > article')].slice(0,2);
      const underHtml=under.length?`<div class="ent-underreported-links"><strong>UNDERREPORTED CONNECTION</strong>${under.map(r=>`<a href="${safe(text(r,'link'))}" target="_blank" rel="noopener noreferrer">${safe(text(r,'title'))}${text(r,'source')?` <span>· ${safe(text(r,'source'))}</span>`:''}</a>`).join('')}</div>`:'';
      const imageHtml=image?`<a class="ent-image-link" href="${safe(link)}" target="_blank" rel="noopener noreferrer"><img class="ent-card-image" src="${safe(image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.closest('.ent-image-link')?.remove()"></a>`:'';
      const cls=safe(label.toLowerCase().replace(/[^a-z]+/g,'-'));
      ar.innerHTML=`<div class="ent-card-flags"><span class="ent-tier ${cls}">${safe(label)}</span>${tier==='under-the-radar'?'<span class="ent-radar-note">UNDER THE RADAR</span>':''}${mode==='dirty'?'<span class="ent-broad-note">DIRTY</span>':''}</div>${imageHtml}<h3><a href="${safe(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${safe(title)}</a></h3>${desc?`<p class="description">${safe(desc)}</p>`:''}${why?`<div class="why">${safe(why)}</div>`:''}${underHtml}<div class="meta"><span>${safe(typeof formatDate==='function'?formatDate(date):date)}</span>${source?`<span class="source">${safe(source)}</span>`:''}</div>`;
      body.appendChild(ar);
    });
    sec.appendChild(body);root.appendChild(sec);
    if(typeof decorateNewBadges==='function')decorateNewBadges();
    if(typeof appendLoadMoreControl==='function')appendLoadMoreControl(data);
  }

  function install(){
    if(!ensureTab())return false;
    window.__categoryRenderers=window.__categoryRenderers||{};window.__categoryRenderers[KEY]=renderEntertainment;
    if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();
    if(typeof active!=='undefined'&&active===KEY&&typeof canonicalRender==='function'&&typeof allItems!=='undefined')canonicalRender(allItems);
    return true;
  }

  const style=document.createElement('style');style.id='entertainment-v4-style';
  style.textContent='.ent-section-header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.ent-section-header h2{margin-right:0}.ent-section-header .count{margin-left:auto}.ent-mode-state,.ent-tier,.ent-radar-note,.ent-broad-note{display:inline-flex;border-radius:999px;font-weight:900;letter-spacing:.07em}.ent-mode-state{padding:3px 7px;font-size:8px}.ent-mode-state.clean{background:rgba(22,163,74,.09);color:#15803d}.ent-mode-state.dirty{background:rgba(234,88,12,.09);color:#c2410c}.ent-mode-toggle{border:1px solid rgba(190,24,93,.28);background:rgba(190,24,93,.08);color:#be185d;border-radius:999px;padding:5px 10px;font-size:9px;font-weight:900;letter-spacing:.08em;cursor:pointer}.ent-card-flags{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0 0 7px}.ent-tier,.ent-radar-note,.ent-broad-note{padding:3px 7px;font-size:8.5px}.ent-tier{background:rgba(190,24,93,.10);color:#be185d;border:1px solid rgba(190,24,93,.22)}.ent-radar-note{background:rgba(100,116,139,.10);color:#475569;border:1px solid rgba(100,116,139,.18)}.ent-broad-note{background:rgba(15,23,42,.08);color:#475569;border:1px solid rgba(15,23,42,.15)}.ent-tier.major,.ent-tier.adult-business-legal{background:rgba(220,38,38,.09);color:#b91c1c;border-color:rgba(220,38,38,.2)}.ent-tier.people-family,.ent-tier.philanthropy{background:rgba(22,163,74,.08);color:#15803d;border-color:rgba(22,163,74,.18)}.ent-tier.creator,.ent-tier.adult-industry,.ent-tier.adult-awards{background:rgba(124,58,237,.08);color:#6d28d9;border-color:rgba(124,58,237,.18)}.ent-tier.mature-fashion,.ent-tier.nude-photo-shoot{background:rgba(234,88,12,.08);color:#c2410c;border-color:rgba(234,88,12,.18)}.ent-image-link{display:block;margin:0 0 10px;border-radius:10px;overflow:hidden;background:rgba(100,116,139,.08)}.ent-card-image{display:block;width:100%;max-height:320px;object-fit:cover;aspect-ratio:16/9}.ent-underreported-links{margin-top:10px;padding:9px 10px;border-left:4px solid #dc2626;background:rgba(220,38,38,.06);border-radius:8px}.ent-underreported-links strong{display:block;margin-bottom:4px;color:#dc2626;font-size:8.5px}.ent-underreported-links a{display:block;margin-top:4px;color:#dc2626!important;text-decoration:none;font-size:10.5px;font-weight:800}.ent-underreported-links span{font-weight:600;opacity:.8}@media(max-width:600px){.ent-section-header .count{width:100%;margin-left:0;font-size:9px}.ent-mode-toggle{padding:4px 8px;font-size:8px}}';
  document.head.appendChild(style);
  let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},50);
  window.__entertainmentV4=true;
})();
