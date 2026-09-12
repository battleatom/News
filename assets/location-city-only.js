(function(){
  'use strict';
  if(window.__locationCityOnlyV1)return;
  const SCOPE_KEY='underreported-location-scope';

  function migrateCountyScope(){
    try{
      if(localStorage.getItem(SCOPE_KEY)==='county')localStorage.setItem(SCOPE_KEY,'local');
    }catch(e){}
  }

  function removeCountyScope(){
    migrateCountyScope();
    document.querySelectorAll('.location-scope-bar .location-scope-btn[data-scope="county"]').forEach(btn=>btn.remove());
  }

  migrateCountyScope();
  const observer=new MutationObserver(removeCountyScope);
  const start=()=>{
    removeCountyScope();
    const root=document.getElementById('news-feed')||document.body;
    if(root)observer.observe(root,{childList:true,subtree:true});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('underreported:location',()=>setTimeout(removeCountyScope,0));
  window.__locationCityOnlyV1=true;
})();
