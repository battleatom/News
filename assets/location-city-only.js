(function(){
  'use strict';
  if(window.__locationCityOnlyV2)return;
  const SCOPE_KEY='underreported-location-scope';

  function migrateCountyScope(){
    try{
      if(localStorage.getItem(SCOPE_KEY)==='county')localStorage.setItem(SCOPE_KEY,'state');
    }catch(e){}
  }

  function consolidateStateCountyScope(){
    migrateCountyScope();
    document.querySelectorAll('.location-scope-bar .location-scope-btn[data-scope="county"]').forEach(btn=>btn.remove());
    document.querySelectorAll('.location-scope-bar .location-scope-btn[data-scope="state"]').forEach(btn=>{
      const count=(btn.textContent||'').match(/\((\d+)\)\s*$/);
      btn.textContent=count?`State & County (${count[1]})`:'State & County';
      btn.setAttribute('aria-label','State and county news');
    });
  }

  migrateCountyScope();
  const observer=new MutationObserver(consolidateStateCountyScope);
  const start=()=>{
    consolidateStateCountyScope();
    const root=document.getElementById('news-feed')||document.body;
    if(root)observer.observe(root,{childList:true,subtree:true});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('underreported:location',()=>setTimeout(consolidateStateCountyScope,0));
  window.__locationCityOnlyV2=true;
})();
