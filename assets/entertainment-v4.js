(function(){
  'use strict';
  if(window.__entertainmentV4)return;
  const KEY='entertainment', LABEL='🎭 Entertainment', ACCENT='#be185d';

  const text=(item,tag)=>item.querySelector(tag)?.textContent?.trim()||'';
  const safe=v=>typeof esc==='function'?esc(v):String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  // Entertainment image rendering intentionally inactive. Upstream image URLs were unreliable and did not render consistently.

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

  function entertainmentItems(items){
    return items.filter(item=>{
      if(text(item,'category')!==KEY)return false;
      return (text(item,'entertainmentSafety')||'clean').toLowerCase()!=='dirty';
    });
  }

  function renderEntertainment(items){
    const ordered=entertainmentItems(items);
    const data=typeof paginatedNewsItems==='function'?paginatedNewsItems(ordered):{available:ordered,visible:ordered,count:ordered.length};
    const root=document.getElementById('news-feed');if(!root)return;root.innerHTML='';
    const sec=document.createElement('section');sec.className='section entertainment-section';sec.style.setProperty('--accent',ACCENT);
    const head=document.createElement('div');head.className='section-header ent-section-header';
    head.innerHTML=`<h2>${LABEL}</h2><span class="count">Showing ${data.count} of ${data.available.length} stories</span>`;
    sec.appendChild(head);

    const intro=document.createElement('div');intro.className='x-issues-intro';
    intro.textContent='Major entertainment, careers, awards, family news, releases and industry developments. Ranked by importance first, then recency.';
    sec.appendChild(intro);

    const body=document.createElement('div');body.className='section-body';
    if(!data.visible.length)body.innerHTML='<div class="empty">No verified entertainment stories are available right now.</div>';
    data.visible.forEach((item,i)=>{
      const ar=document.createElement('article');ar.className='news-item entertainment-item';
      const title=text(item,'title')||'Untitled', link=text(item,'link')||'#', desc=text(item,'description'), why=text(item,'whyMatters');
      const date=text(item,'pubDate'), source=text(item,'source');
      const label=text(item,'entertainmentLabel')||'ENTERTAINMENT';
      const under=[...item.querySelectorAll('underreportedLinks > article')].slice(0,2);
      const underHtml=under.length?`<div class="ent-underreported-links"><strong>UNDERREPORTED CONNECTION</strong>${under.map(r=>`<a href="${safe(text(r,'link'))}" target="_blank" rel="noopener noreferrer">${safe(text(r,'title'))}${text(r,'source')?` <span>· ${safe(text(r,'source'))}</span>`:''}</a>`).join('')}</div>`:'';
      const cls=safe(label.toLowerCase().replace(/[^a-z]+/g,'-'));
      ar.innerHTML=`<div class="ent-card-flags"><span class="ent-tier ${cls}">${safe(label)}</span></div><h3><a href="${safe(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${safe(title)}</a></h3>${desc?`<p class="description">${safe(desc)}</p>`:''}${why?`<div class="why">${safe(why)}</div>`:''}${underHtml}<div class="meta"><span>${safe(typeof formatDate==='function'?formatDate(date):date)}</span>${source?`<span class="source">${safe(source)}</span>`:''}</div>`;
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
  style.textContent='.ent-section-header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.ent-section-header h2{margin-right:0}.ent-section-header .count{margin-left:auto}.ent-tier{display:inline-flex;border-radius:999px;font-weight:900;letter-spacing:.07em;padding:3px 7px;font-size:8.5px;background:rgba(190,24,93,.10);color:#be185d;border:1px solid rgba(190,24,93,.22)}.ent-card-flags{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0 0 7px}.ent-tier.major{background:rgba(220,38,38,.09);color:#b91c1c;border-color:rgba(220,38,38,.2)}.ent-tier.people-family,.ent-tier.philanthropy{background:rgba(22,163,74,.08);color:#15803d;border-color:rgba(22,163,74,.18)}.ent-underreported-links{margin-top:10px;padding:9px 10px;border-left:4px solid #dc2626;background:rgba(220,38,38,.06);border-radius:8px}.ent-underreported-links strong{display:block;margin-bottom:4px;color:#dc2626;font-size:8.5px}.ent-underreported-links a{display:block;margin-top:4px;color:#dc2626!important;text-decoration:none;font-size:10.5px;font-weight:800}.ent-underreported-links span{font-weight:600;opacity:.8}@media(max-width:600px){.ent-section-header .count{width:100%;margin-left:0;font-size:9px}}';
  document.head.appendChild(style);
  let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},50);
  window.__entertainmentV4=true;
})();
