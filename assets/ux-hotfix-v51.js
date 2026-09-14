(()=>{
  'use strict';

  const RAIL_COLORS={
    blue:'#2563eb',
    green:'#16a34a',
    orange:'#f97316',
    purple:'#9333ea',
    red:'#dc2626'
  };
  const RAIL_CLASSES=['rail-blue','rail-green','rail-orange','rail-purple','rail-red'];

  function canonicalTabKey(value){
    let text=String(value||'').toLowerCase().trim();
    text=text.replace(/[^a-z0-9&]+/g,' ').replace(/\s+/g,' ').trim();
    const compact=text.replace(/[^a-z0-9]+/g,'');
    const aliases={
      boxoffice:'boxoffice',
      boxofficemovies:'boxoffice',
      topstories:'top',
      topissues:'x',
      unitedstates:'us',
      federalgovernment:'federal',
      lawslegislation:'legislation',
      newmexico:'nm',
      gamingcomputing:'gaming',
      militarywar:'military'
    };
    return aliases[compact]||compact||'unknown';
  }

  function activeTabKey(){
    try{
      if(typeof active!=='undefined'&&active)return canonicalTabKey(active);
    }catch(e){}
    if(window.active)return canonicalTabKey(window.active);
    const selected=document.querySelector('.tab.active');
    if(selected){
      const raw=selected.dataset.category||selected.dataset.tab||selected.dataset.key||selected.textContent;
      if(raw)return canonicalTabKey(raw);
    }
    return canonicalTabKey(document.body?.dataset?.activeTab||'');
  }

  function clearBoxOfficeFeedback(root=document){
    if(activeTabKey()!=='boxoffice')return;
    root.querySelectorAll?.('.card-feedback-controls').forEach(el=>el.remove());
    root.querySelectorAll?.('.news-item.has-card-feedback').forEach(card=>card.classList.remove('has-card-feedback'));
  }

  function importanceBand(card){
    const title=card.querySelector('h3,h2,.title,.headline')?.textContent||'';
    const desc=card.querySelector('.description,.summary,.dek')?.textContent||'';
    const text=` ${title} ${desc} `.toLowerCase();
    if(/\b(breaking|deadly|killed|mass shooting|earthquake|hurricane|wildfire|evacuat(?:e|ion)|airstrike|missile strike|invasion|ceasefire|state of emergency|major outage|data breach|cyberattack)\b/.test(text))return 'red';
    if(/\b(developing|investigation|indict(?:ed|ment)|arrest(?:ed)?|lawsuit|court rules?|strike|shutdown|recall|outbreak|tariffs?|layoffs?|bankruptcy|fraud|charges?)\b/.test(text))return 'orange';
    if(/\b(congress|senate|house of representatives|white house|president|federal|supreme court|legislation|\bbill\b|executive order|election|voters?|governor|policy|regulation|rulemaking)\b/.test(text))return 'purple';
    if(/\b(science|research|study finds?|breakthrough|discovery|health|medical|renewable|education|achievement|award|solution|conservation|recovery)\b/.test(text))return 'green';
    return 'blue';
  }

  function applyRail(card){
    if(!(card instanceof Element))return;
    if(card.classList.contains('underreported-item')||card.classList.contains('nfl-game-card'))return;
    if(activeTabKey()==='boxoffice')return;
    const band=importanceBand(card);
    RAIL_CLASSES.forEach(cls=>card.classList.remove(cls));
    card.classList.add(`rail-${band}`);
    card.dataset.railHierarchy=band;
    // Inline !important is deliberate: generated legacy card CSS can load after
    // v5-visual.css, so this guarantees the semantic left rail remains visible.
    card.style.setProperty('border-left',`4px solid ${RAIL_COLORS[band]}`,'important');
  }

  function apply(root=document){
    clearBoxOfficeFeedback(root);
    if(activeTabKey()==='boxoffice')return;
    if(root instanceof Element&&root.matches('.news-item'))applyRail(root);
    root.querySelectorAll?.('.news-item').forEach(applyRail);
  }

  function start(){
    apply(document);
    const observer=new MutationObserver(mutations=>{
      let relevant=false;
      for(const mutation of mutations){
        if(mutation.type==='childList'&&mutation.addedNodes.length){relevant=true;break;}
        if(mutation.type==='attributes'){relevant=true;break;}
      }
      if(relevant)requestAnimationFrame(()=>apply(document));
    });
    observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','data-category','data-tab']});
    document.addEventListener('click',event=>{
      if(event.target.closest('.tab'))requestAnimationFrame(()=>requestAnimationFrame(()=>apply(document)));
    });
    window.addEventListener('pageshow',()=>apply(document),{passive:true});
    document.documentElement.dataset.uxHotfixV51='ready';
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
