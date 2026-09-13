/* Underreported V5 hierarchy bridge.
   Canonical cards carry data-hierarchy at render time. This bridge is now a
   compatibility fallback for special/legacy renderers only. */
(function(){
  'use strict';

  const HIERARCHY_CLASSES=['v5-hierarchy-high','v5-hierarchy-analysis','v5-hierarchy-local','v5-hierarchy-trending','v5-hierarchy-standard'];
  const LOCAL_SECTIONS=new Set(['nm','local','region']);
  const HIGH_FIRST_SECTIONS=new Set(['top','world','us','presidential','federal','military']);

  function currentSection(card){
    const bound=card?.closest?.('.section')?.dataset?.section||card?.dataset?.section||'';
    if(bound)return String(bound);
    try{if(typeof active!=='undefined'&&active)return String(active);}catch(e){}
    return document.body?.dataset?.activeTab||'';
  }

  function classify(card,index,section){
    if(card.classList.contains('nfl-game-card'))return '';
    const bound=card.dataset.hierarchy||card.dataset.v5Hierarchy||'';
    if(bound)return bound;
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
    const kind=classify(card,index,section||currentSection(card));
    const expectedClass=kind?'v5-hierarchy-'+kind:'';
    const currentKind=card.dataset.v5Hierarchy||'';

    if(!kind){
      if(currentKind||HIERARCHY_CLASSES.some(cls=>card.classList.contains(cls))){
        HIERARCHY_CLASSES.forEach(cls=>card.classList.remove(cls));
        delete card.dataset.v5Hierarchy;
        delete card.dataset.hierarchy;
      }
      return;
    }

    if(currentKind!==kind||!card.classList.contains(expectedClass)){
      HIERARCHY_CLASSES.forEach(cls=>{if(cls!==expectedClass)card.classList.remove(cls);});
      card.classList.add(expectedClass);
      card.dataset.v5Hierarchy=kind;
    }
    if(card.dataset.hierarchy!==kind)card.dataset.hierarchy=kind;

    let badge=card.querySelector(':scope > .v3-importance');
    if(!badge){
      badge=document.createElement('span');
      card.prepend(badge);
    }
    const expectedBadgeClass='v3-importance '+kind;
    const expectedLabel=labelFor(kind);
    if(badge.className!==expectedBadgeClass)badge.className=expectedBadgeClass;
    if(badge.textContent!==expectedLabel)badge.textContent=expectedLabel;
    if(badge.getAttribute('data-v5-hierarchy-badge')!==kind)badge.setAttribute('data-v5-hierarchy-badge',kind);
  }

  function apply(root=document){
    const cards=[...document.querySelectorAll('#news-feed .news-item')];
    cards.forEach((card,index)=>decorateCard(card,index,currentSection(card)));
    if(document.body&&document.body.dataset.v5Hierarchy!=='active')document.body.dataset.v5Hierarchy='active';
  }

  let queued=false;
  function queue(){
    if(queued)return;
    queued=true;
    requestAnimationFrame(()=>{queued=false;apply();});
  }

  function containsStoryNode(node){
    if(!node||node.nodeType!==1)return false;
    if(node.matches?.('.news-item'))return true;
    return Boolean(node.querySelector?.('.news-item'));
  }

  function feedChanged(mutations){
    for(const mutation of mutations){
      for(const node of mutation.addedNodes){if(containsStoryNode(node))return true;}
    }
    return false;
  }

  function start(){
    apply();
    const feed=document.getElementById('news-feed');
    const tabs=document.getElementById('tabs');
    if(feed)new MutationObserver(mutations=>{if(feedChanged(mutations))queue();}).observe(feed,{childList:true,subtree:true});
    if(tabs)new MutationObserver(queue).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    document.addEventListener('click',e=>{if(e.target.closest('.tab'))requestAnimationFrame(queue);});
    document.addEventListener('underreported:feed-rendered',queue);
    window.addEventListener('underreported:location',queue,{passive:true});
    window.__underreportedV5Hierarchy=true;
  }

  window.UnderreportedHierarchy={apply,decorateCard};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
