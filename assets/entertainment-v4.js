(function(){
  'use strict';
  if(window.__entertainmentV4)return;

  const KEY='entertainment';
  const LABEL='🎭 Entertainment';
  const ACCENT='#be185d';
  const MODE_KEY='underreported-entertainment-mode';

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

  function text(item,tag){return item.querySelector(tag)?.textContent?.trim()||''}
  function safe(v){return typeof esc==='function'?esc(v):String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  function safeImage(v){try{const u=new URL(v,location.href);return /^https?:$/.test(u.protocol)?u.href:''}catch(e){return ''}}

  function currentMode(){
    try{
      const fromUrl=new URL(location.href).searchParams.get('entmode');
      if(fromUrl==='clean'||fromUrl==='dirty'){
        localStorage.setItem(MODE_KEY,fromUrl);
        return fromUrl;
      }
    }catch(e){}
    return localStorage.getItem(MODE_KEY)==='clean'?'clean':'dirty';
  }

  function entertainmentItems(items){
    return items.filter(item=>text(item,'category')===KEY);
  }

  function modeOrdered(items){
    const mode=currentMode();
    const all=entertainmentItems(items);
    if(mode==='clean')return all.filter(item=>(text(item,'entertainmentSafety')||'clean')!=='dirty');

    // Preserve the importance-ranked feed, but make broad mode visibly broader on the first page.
    // Dirty-only cards are surfaced after the highest-priority core stories rather than buried below the fold.
    const clean=all.filter(item=>(text(item,'entertainmentSafety')||'clean')!=='dirty');
    const broad=all.filter(item=>(text(item,'entertainmentSafety')||'clean')==='dirty');
    if(!broad.length)return all;

    const out=[];
    const used=new Set();
    const push=item=>{if(item&&!used.has(item)){used.add(item);out.push(item)}};

    clean.slice(0,5).forEach(push);
    push(broad[0]);
    clean.slice(5,8).forEach(push);
    push(broad[1]);
    all.forEach(push);
    return out;
  }

  function switchMode(mode){
    const next=mode==='dirty'?'clean':'dirty';
    try{localStorage.setItem(MODE_KEY,next)}catch(e){}
    try{
      if(typeof loadCounts!=='undefined')loadCounts[KEY]=typeof STORIES_PER_PAGE!=='undefined'?STORIES_PER_PAGE:10;
    }catch(e){}
    const u=new URL(location.href);
    u.searchParams.set('entmode',next);
    u.searchParams.set('entv',Date.now());
    location.href=u.toString();
  }

  function renderEntertainment(items){
    const mode=currentMode();
    const ordered=modeOrdered(items);
    const data=typeof paginatedNewsItems==='function'?paginatedNewsItems(ordered):{available:ordered,visible:ordered,count:ordered.length};
    const root=document.getElementById('news-feed');
    if(!root)return;
    root.innerHTML='';

    const sec=document.createElement('section');
    sec.className='section entertainment-section';
    sec.style.setProperty('--accent',ACCENT);
    const head=document.createElement('div');
    head.className='section-header ent-section-header';
    const actionLabel=mode==='dirty'?'CLEAN':'DIRTY';
    const modeTitle=mode==='dirty'?'Broad entertainment is on. Switch to the cleaner professional-news feed.':'Clean entertainment is on. Switch back to broad entertainment, gossip and lifestyle coverage.';
    head.innerHTML=`<h2>${LABEL}</h2><span class="ent-mode-state ${mode}">${mode==='dirty'?'DIRTY MODE':'CLEAN MODE'}</span><button class="ent-mode-toggle ${mode}" type="button" title="${safe(modeTitle)}" aria-label="${safe(modeTitle)}">${actionLabel}</button><span class="count">Showing ${data.count} of ${data.available.length} stories</span>`;
    sec.appendChild(head);
    head.querySelector('.ent-mode-toggle')?.addEventListener('click',()=>switchMode(mode));

    const intro=document.createElement('div');
    intro.className='x-issues-intro';
    intro.textContent=mode==='clean'
      ?'CLEAN mode prioritizes consequential professional entertainment news: major developments, careers, productions, releases, contracts and industry changes.'
      :'DIRTY mode includes the Clean feed plus verified celebrity life, philanthropy, family, dating/gossip, fashion/red-carpet coverage, nudity-related headlines and adult-industry news. Explicit preview images are not shown.';
    sec.appendChild(intro);

    const body=document.createElement('div');
    body.className='section-body';
    if(!data.visible.length)body.innerHTML='<div class="empty">No verified entertainment stories are available in this mode right now.</div>';

    data.visible.forEach((item,i)=>{
      const ar=document.createElement('article');
      ar.className='news-item entertainment-item';
      const title=text(item,'title')||'Untitled';
      const link=text(item,'link')||'#';
      const desc=text(item,'description');
      const why=text(item,'whyMatters');
      const date=text(item,'pubDate');
      const source=text(item,'source');
      const image=safeImage(text(item,'imageUrl'));
      const label=text(item,'entertainmentLabel')||'ENTERTAINMENT';
      const tier=text(item,'entertainmentTier');
      const safety=text(item,'entertainmentSafety')||'clean';
      const tierHtml=tier==='under-the-radar'?'<span class="ent-radar-note">UNDER THE RADAR</span>':'';
      const under=[...item.querySelectorAll('underreportedLinks > article')].slice(0,2);
      const underHtml=under.length?`<div class="ent-underreported-links"><strong>UNDERREPORTED CONNECTION</strong>${under.map(r=>{const rt=text(r,'title'),rl=text(r,'link'),rs=text(r,'source');return `<a href="${safe(rl)}" target="_blank" rel="noopener noreferrer">${safe(rt)}${rs?` <span>· ${safe(rs)}</span>`:''}</a>`}).join('')}</div>`:'';
      const imageHtml=image?`<a class="ent-image-link" href="${safe(link)}" target="_blank" rel="noopener noreferrer"><img class="ent-card-image" src="${safe(image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.closest('.ent-image-link')?.remove()"></a>`:'';
      ar.innerHTML=`<div class="ent-card-flags"><span class="ent-tier ${safe(label.toLowerCase().replace(/[^a-z]+/g,'-'))}">${safe(label)}</span>${tierHtml}${mode==='dirty'&&safety==='dirty'?'<span class="ent-broad-note">BROAD</span>':''}</div>${imageHtml}<h3><a href="${safe(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${safe(title)}</a></h3>${desc?`<p class="description">${safe(desc)}</p>`:''}${why?`<div class="why">${safe(why)}</div>`:''}${underHtml}<div class="meta"><span>${safe(typeof formatDate==='function'?formatDate(date):date)}</span>${source?`<span class="source">${safe(source)}</span>`:''}</div>`;
      body.appendChild(ar);
    });

    sec.appendChild(body);
    root.appendChild(sec);
    if(typeof decorateNewBadges==='function')decorateNewBadges();
    if(typeof appendLoadMoreControl==='function')appendLoadMoreControl(data);
  }

  function install(){
    if(!ensureTab())return false;
    window.__categoryRenderers=window.__categoryRenderers||{};
    window.__categoryRenderers[KEY]=renderEntertainment;
    if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();
    if(typeof active!=='undefined'&&active===KEY&&typeof canonicalRender==='function'&&typeof allItems!=='undefined')canonicalRender(allItems);
    return true;
  }

  const style=document.createElement('style');
  style.id='entertainment-v4-style';
  style.textContent='.ent-section-header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.ent-section-header h2{margin-right:0}.ent-section-header .count{margin-left:auto}.ent-mode-state{display:inline-flex;padding:3px 7px;border-radius:999px;font-size:8px;font-weight:900;letter-spacing:.08em;background:rgba(15,23,42,.07);color:#475569}.ent-mode-state.clean{background:rgba(22,163,74,.09);color:#15803d}.ent-mode-state.dirty{background:rgba(234,88,12,.09);color:#c2410c}.ent-mode-toggle{border:1px solid rgba(190,24,93,.28);background:rgba(190,24,93,.08);color:#be185d;border-radius:999px;padding:5px 10px;font-size:9px;font-weight:900;letter-spacing:.08em;cursor:pointer;box-shadow:none}.ent-mode-toggle:hover{background:rgba(190,24,93,.14)}.ent-mode-toggle.clean{border-color:rgba(71,85,105,.28);background:rgba(71,85,105,.08);color:#475569}.ent-card-flags{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0 0 7px}.ent-tier,.ent-radar-note,.ent-broad-note{display:inline-flex;padding:3px 7px;border-radius:999px;font-size:8.5px;font-weight:900;letter-spacing:.08em}.ent-tier{background:rgba(190,24,93,.10);color:#be185d;border:1px solid rgba(190,24,93,.22)}.ent-tier.major{background:rgba(220,38,38,.09);color:#b91c1c;border-color:rgba(220,38,38,.2)}.ent-tier.career{background:rgba(37,99,235,.08);color:#1d4ed8;border-color:rgba(37,99,235,.18)}.ent-tier.people{background:rgba(124,58,237,.08);color:#6d28d9;border-color:rgba(124,58,237,.18)}.ent-tier.lifestyle{background:rgba(234,88,12,.08);color:#c2410c;border-color:rgba(234,88,12,.18)}.ent-radar-note{background:rgba(100,116,139,.10);color:#475569;border:1px solid rgba(100,116,139,.18)}.ent-broad-note{background:rgba(15,23,42,.08);color:#475569;border:1px solid rgba(15,23,42,.15)}.ent-image-link{display:block;margin:0 0 10px;border-radius:10px;overflow:hidden;background:rgba(100,116,139,.08)}.ent-card-image{display:block;width:100%;max-height:320px;object-fit:cover;aspect-ratio:16/9}.ent-underreported-links{margin-top:10px;padding:9px 10px;border-left:4px solid #dc2626;background:rgba(220,38,38,.06);border-radius:8px}.ent-underreported-links strong{display:block;margin-bottom:4px;color:#dc2626;font-size:8.5px;letter-spacing:.08em}.ent-underreported-links a{display:block;margin-top:4px;color:#dc2626!important;text-decoration:none;font-size:10.5px;font-weight:800;line-height:1.35}.ent-underreported-links a:hover{text-decoration:underline}.ent-underreported-links span{font-weight:600;opacity:.8}@media (min-width:800px){.ent-card-image{max-height:360px}}@media(max-width:600px){.ent-section-header{gap:6px}.ent-mode-toggle{padding:4px 8px;font-size:8px}.ent-mode-state{font-size:7.5px}.ent-section-header .count{width:100%;margin-left:0;font-size:9px}}';
  document.head.appendChild(style);

  let tries=0;
  const timer=setInterval(()=>{
    tries++;
    if(install()||tries>40)clearInterval(timer);
  },50);

  window.__entertainmentV4=true;
})();