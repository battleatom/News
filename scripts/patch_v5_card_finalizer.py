#!/usr/bin/env python3
from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

marker = '<script id="v5-card-finalizer-v1">'
while marker in s:
    a = s.find(marker)
    b = s.find('</script>', a)
    if b < 0:
        break
    s = s[:a] + s[b + len('</script>'):]

SCRIPT = r'''<script id="v5-card-finalizer-v1">
(function(){
  'use strict';
  if(window.__v5CardFinalizerV1)return;
  window.__v5CardFinalizerV1=true;

  const COLORS={high:'#dc2626',analysis:'#7c3aed',local:'#15803d',trending:'#2563eb',standard:'#64748b'};
  const AGE_COLORS={blue:'#2563eb',green:'#16a34a',orange:'#f97316',purple:'#9333ea',red:'#dc2626'};
  const LABELS={high:'HIGH IMPACT',analysis:'ANALYSIS',local:'LOCAL',trending:'TRENDING',standard:'STANDARD'};
  const CLASSES=['v5-hierarchy-high','v5-hierarchy-analysis','v5-hierarchy-local','v5-hierarchy-trending','v5-hierarchy-standard'];

  function sectionFor(card){
    const explicit=String(card?.dataset?.section||'').trim();
    if(explicit)return explicit;
    const nested=String(card?.closest?.('.section')?.dataset?.section||'').trim();
    if(nested)return nested;
    try{if(typeof active!=='undefined'&&active)return String(active)}catch(e){}
    return String(document.body?.dataset?.activeTab||'');
  }

  function hierarchyKind(section,index){
    if(section==='x')return 'trending';
    if(section==='nm'||section==='local'||section==='region')return 'local';
    if(index===0&&['top','world','us','presidential','federal','military'].includes(section))return 'high';
    return 'standard';
  }

  function ageBandFor(card){
    const direct=String(card.dataset.ageBand||'').toLowerCase();
    if(AGE_COLORS[direct])return direct;
    for(const band of Object.keys(AGE_COLORS))if(card.classList.contains('age-'+band))return band;
    const raw=card.dataset.publishedAt||card.dataset.pubDate||card.querySelector('.meta span:first-child')?.textContent||'';
    const ms=Date.parse(raw);
    if(!Number.isFinite(ms))return 'red';
    const days=Math.max(0,(Date.now()-ms)/86400000);
    if(days<=2)return 'blue';
    if(days<=4)return 'green';
    if(days<=7)return 'orange';
    if(days<=10)return 'purple';
    return 'red';
  }

  function setRail(card,color,width=5){
    card.style.setProperty('--card-rail',color);
    card.style.setProperty('border-left',`${width}px solid ${color}`,'important');
  }

  function syncHierarchyBadge(card,kind){
    let badge=card.querySelector(':scope > .v3-importance');
    if(!badge){badge=document.createElement('span');card.prepend(badge)}
    badge.className='v3-importance '+kind;
    badge.dataset.v5HierarchyBadge=kind;
    badge.textContent=LABELS[kind];
  }

  function normalizeLink(v){
    try{const u=new URL(String(v||''),location.href);u.hash='';return u.href}catch(e){return String(v||'').trim()}
  }

  function syncNewBadge(card){
    const h=card.querySelector('h3');
    if(!h)return;
    const link=normalizeLink(card.dataset.storyUrl||card.querySelector('h3 a[href]')?.href||'');
    const pub=Date.parse(card.dataset.publishedAt||'')||0;
    const first=typeof window.__firstSeenForV26==='function'?Number(window.__firstSeenForV26(link)||0):0;
    const state=typeof window.__classifyNewBadgeV26==='function'?window.__classifyNewBadgeV26(pub,first,Date.now()):'';
    let badge=h.querySelector('.new-badge');
    if(!state){if(badge)badge.remove();return}
    if(!badge){badge=document.createElement('span');badge.className='new-badge';badge.textContent='NEW';h.appendChild(badge)}
    badge.classList.remove('new-badge-red','new-badge-blue','new-badge-yellow');
    badge.classList.add('new-badge-'+state);
    badge.dataset.newState=state;
  }

  function finalizeStoryCard(card,index=0){
    if(!card||card.classList.contains('nfl-game-card'))return card;
    const section=sectionFor(card);
    card.dataset.section=section;
    card.dataset.rank=card.dataset.rank||String(index+1);
    const link=card.querySelector('h3 a[href]')?.href||'';
    if(link&&!card.dataset.storyUrl)card.dataset.storyUrl=link;

    if(card.classList.contains('underreported-item')||section==='underreported'){
      CLASSES.forEach(c=>card.classList.remove(c));
      delete card.dataset.hierarchy;
      delete card.dataset.v5Hierarchy;
      const oldBadge=card.querySelector(':scope > .v3-importance');
      if(oldBadge)oldBadge.remove();
      const band=ageBandFor(card);
      card.dataset.ageBand=band;
      card.classList.remove('age-blue','age-green','age-orange','age-purple','age-red');
      card.classList.add('age-'+band);
      setRail(card,AGE_COLORS[band],5);
      syncNewBadge(card);
      card.dataset.cardFinalized='v1';
      return card;
    }

    const kind=hierarchyKind(section,index);
    CLASSES.forEach(c=>card.classList.remove(c));
    card.classList.add('v5-hierarchy-'+kind);
    card.dataset.hierarchy=kind;
    card.dataset.v5Hierarchy=kind;
    setRail(card,COLORS[kind],kind==='standard'?3:5);
    syncHierarchyBadge(card,kind);
    syncNewBadge(card);
    card.dataset.cardFinalized='v1';
    return card;
  }

  function finalizeAllStoryCards(){
    const cards=[...document.querySelectorAll('#news-feed .news-item')];
    cards.forEach((card,index)=>finalizeStoryCard(card,index));
    document.body?.setAttribute('data-v5-card-finalizer','active');
    return cards.length;
  }

  window.finalizeStoryCard=finalizeStoryCard;
  window.finalizeAllStoryCards=finalizeAllStoryCards;

  function installRenderWrapper(){
    const previous=window.canonicalRender||window.render;
    if(typeof previous!=='function'||previous.__v5FinalizerWrapped)return;
    const wrapped=function(...args){
      const out=previous.apply(this,args);
      finalizeAllStoryCards();
      requestAnimationFrame(finalizeAllStoryCards);
      return out;
    };
    wrapped.__v5FinalizerWrapped=true;
    wrapped.__v5Previous=previous;
    window.canonicalRender=wrapped;
    window.render=wrapped;
    try{canonicalRender=wrapped;render=wrapped}catch(e){}
  }

  installRenderWrapper();
  document.addEventListener('underreported:feed-rendered',finalizeAllStoryCards);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{installRenderWrapper();finalizeAllStoryCards()},{once:true});
  else finalizeAllStoryCards();
})();
</script>'''

if '</body>' not in s:
    raise SystemExit('Generated page is missing </body>')
s = s.replace('</body>', SCRIPT + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Installed authoritative V5 card finalizer with inline rail ownership and direct NEW synchronization.')
