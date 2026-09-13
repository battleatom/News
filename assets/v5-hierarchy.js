/* Underreported V5 hierarchy bridge.
   Presentation-only: preserves V4 feed, ranking, routing, refresh, and card sizing behavior. */
(function(){
  'use strict';

  const HIERARCHY_CLASSES=['v5-hierarchy-high','v5-hierarchy-analysis','v5-hierarchy-local','v5-hierarchy-trending','v5-hierarchy-standard'];
  const LOCAL_SECTIONS=new Set(['nm','local','region']);
  const HIGH_FIRST_SECTIONS=new Set(['top','world','us','presidential','federal','military']);

  function currentSection(){
    try{if(typeof active!=='undefined'&&active)return String(active);}catch(e){}
    return document.body?.dataset?.activeTab||'';
  }

  function classify(card,index,section){
    if(card.classList.contains('nfl-game-card'))return '';
    if(card.classList.contains('underreported-item')||section==='underreported')return 'analysis';
    if(card.classList.contains('x-issue-item')||section==='x')return 'trending';
    if(LOCAL_SECTIONS.has(section))return 'local';
    if(index===0&&HIGH_FIRST_SECTIONS.has(section))return 'high';
    return 'standard';
  }

  function labelFor(kind){
    return ({high:'HIGH IMPACT',analysis:'ANALYSIS',local:'LOCAL',trending:'TRENDING',standard:'STANDARD'})[kind]||'';
  }

  function decorateCard(card,index,section){
    const kind=classify(card,index,section);
    HIERARCHY_CLASSES.forEach(cls=>card.classList.remove(cls));
    delete card.dataset.v5Hierarchy;
    if(!kind)return;

    card.classList.add('v5-hierarchy-'+kind);
    card.dataset.v5Hierarchy=kind;

    let badge=card.querySelector(':scope > .v3-importance');
    if(!badge){
      badge=document.createElement('span');
      badge.className='v3-importance';
      card.prepend(badge);
    }
    badge.className='v3-importance '+kind;
    badge.textContent=labelFor(kind);
    badge.setAttribute('data-v5-hierarchy-badge',kind);
  }

  function apply(root=document){
    const section=currentSection();
    const cards=[...root.querySelectorAll?.('#news-feed .news-item')||[]];
    cards.forEach((card,index)=>decorateCard(card,index,section));
    if(document.body)document.body.dataset.v5Hierarchy='active';
  }

  let queued=false;
  function queue(){
    if(queued)return;
    queued=true;
    requestAnimationFrame(()=>{queued=false;apply();});
  }

  function start(){
    apply();
    const feed=document.getElementById('news-feed');
    const tabs=document.getElementById('tabs');
    if(feed)new MutationObserver(queue).observe(feed,{childList:true,subtree:true});
    if(tabs)new MutationObserver(queue).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    document.addEventListener('click',e=>{if(e.target.closest('.tab'))requestAnimationFrame(queue);});
    window.addEventListener('underreported:location',queue,{passive:true});
    window.__underreportedV5Hierarchy=true;
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
