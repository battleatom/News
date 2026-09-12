(function(){
  'use strict';
  if(window.__entertainmentV4)return;

  const KEY='entertainment';
  const LABEL='🎭 Entertainment';
  const ACCENT='#be185d';

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

  function renderEntertainment(items){
    const data=typeof paginatedNewsItems==='function'?paginatedNewsItems(items):{available:items.filter(i=>text(i,'category')===KEY),visible:items.filter(i=>text(i,'category')===KEY),count:items.length};
    const root=document.getElementById('news-feed');
    if(!root)return;
    root.innerHTML='';

    const sec=document.createElement('section');
    sec.className='section entertainment-section';
    sec.style.setProperty('--accent',ACCENT);
    const head=document.createElement('div');
    head.className='section-header';
    head.innerHTML=`<h2>${LABEL}</h2><span class="count">Showing ${data.count} of ${data.available.length} stories</span>`;
    sec.appendChild(head);

    const intro=document.createElement('div');
    intro.className='x-issues-intro';
    intro.textContent='The first five stories are the newest verified entertainment reports. After that, credible specialist coverage is prioritized to surface stories that may have received less mainstream attention.';
    sec.appendChild(intro);

    const body=document.createElement('div');
    body.className='section-body';
    if(!data.visible.length)body.innerHTML='<div class="empty">No verified entertainment stories are available right now.</div>';

    data.visible.forEach((item,i)=>{
      const ar=document.createElement('article');
      ar.className='news-item entertainment-item';
      const title=text(item,'title')||'Untitled';
      const link=text(item,'link')||'#';
      const desc=text(item,'description');
      const why=text(item,'whyMatters');
      const date=text(item,'pubDate');
      const source=text(item,'source');
      const tier=text(item,'entertainmentTier')||(i<5?'newest':'under-the-radar');
      const badge=tier==='newest'?'NEWEST':'UNDER THE RADAR';
      const under=[...item.querySelectorAll('underreportedLinks > article')].slice(0,2);
      const underHtml=under.length?`<div class="ent-underreported-links"><strong>UNDERREPORTED CONNECTION</strong>${under.map(r=>{const rt=text(r,'title'),rl=text(r,'link'),rs=text(r,'source');return `<a href="${safe(rl)}" target="_blank" rel="noopener noreferrer">${safe(rt)}${rs?` <span>· ${safe(rs)}</span>`:''}</a>`}).join('')}</div>`:'';
      ar.innerHTML=`<div class="ent-tier ${tier==='newest'?'newest':'radar'}">${badge}</div><h3><a href="${safe(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${safe(title)}</a></h3>${desc?`<p class="description">${safe(desc)}</p>`:''}${why?`<div class="why">${safe(why)}</div>`:''}${underHtml}<div class="meta"><span>${safe(typeof formatDate==='function'?formatDate(date):date)}</span>${source?`<span class="source">${safe(source)}</span>`:''}</div>`;
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
  style.textContent='.ent-tier{display:inline-flex;margin:0 0 7px;padding:3px 7px;border-radius:999px;font-size:8.5px;font-weight:900;letter-spacing:.08em}.ent-tier.newest{background:rgba(190,24,93,.10);color:#be185d;border:1px solid rgba(190,24,93,.22)}.ent-tier.radar{background:rgba(100,116,139,.10);color:#475569;border:1px solid rgba(100,116,139,.18)}.ent-underreported-links{margin-top:10px;padding:9px 10px;border-left:4px solid #dc2626;background:rgba(220,38,38,.06);border-radius:8px}.ent-underreported-links strong{display:block;margin-bottom:4px;color:#dc2626;font-size:8.5px;letter-spacing:.08em}.ent-underreported-links a{display:block;margin-top:4px;color:#dc2626!important;text-decoration:none;font-size:10.5px;font-weight:800;line-height:1.35}.ent-underreported-links a:hover{text-decoration:underline}.ent-underreported-links span{font-weight:600;opacity:.8}';
  document.head.appendChild(style);

  let tries=0;
  const timer=setInterval(()=>{
    tries++;
    if(install()||tries>40)clearInterval(timer);
  },50);

  window.__entertainmentV4=true;
})();
