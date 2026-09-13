(function(){
  'use strict';
  if(window.__locationCityOnlyV3)return;
  const SCOPE_KEY='underreported-location-scope';
  let scheduled=false;

  function migrateCountyScope(){
    try{
      if(localStorage.getItem(SCOPE_KEY)==='county')localStorage.setItem(SCOPE_KEY,'state');
    }catch(e){}
  }

  function consolidateStateCountyScope(){
    migrateCountyScope();
    document.querySelectorAll('.location-scope-bar .location-scope-btn[data-scope="county"]').forEach(btn=>btn.remove());
    document.querySelectorAll('.location-scope-bar .location-scope-btn[data-scope="state"]').forEach(btn=>{
      const current=(btn.textContent||'').trim();
      const count=current.match(/\((\d+)\)\s*$/);
      const desired=count?`State & County (${count[1]})`:'State & County';
      if(current!==desired)btn.textContent=desired;
      if(btn.getAttribute('aria-label')!=='State and county news')btn.setAttribute('aria-label','State and county news');
    });
  }

  function scheduleConsolidation(){
    if(scheduled)return;
    scheduled=true;
    queueMicrotask(()=>{
      scheduled=false;
      consolidateStateCountyScope();
    });
  }

  migrateCountyScope();
  const observer=new MutationObserver(scheduleConsolidation);
  const start=()=>{
    consolidateStateCountyScope();
    const root=document.getElementById('news-feed')||document.body;
    if(root)observer.observe(root,{childList:true,subtree:true});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('underreported:location',scheduleConsolidation);
  window.__locationCityOnlyV3=true;
})();
