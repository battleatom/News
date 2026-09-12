(function(){
  'use strict';
  if(window.__locationCityOnlyV1)return;
  const SCOPE_KEY='underreported-location-scope';

  function normalizeScope(){
    try{
      if(localStorage.getItem(SCOPE_KEY)==='county')localStorage.setItem(SCOPE_KEY,'local');
    }catch(e){}
  }

  function removeCountyControl(){
    normalizeScope();
    document.querySelectorAll('.location-scope-btn[data-scope="county"]').forEach(btn=>btn.remove());
  }

  const style=document.createElement('style');
  style.id='location-city-only-v1-style';
  style.textContent='.location-scope-btn[data-scope="county"]{display:none!important}';
  document.head.appendChild(style);

  const observer=new MutationObserver(removeCountyControl);
  const start=()=>{
    removeCountyControl();
    const root=document.getElementById('news-feed')||document.body;
    observer.observe(root,{childList:true,subtree:true});
  };

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  window.addEventListener('underreported:location',()=>setTimeout(removeCountyControl,0));
  window.__locationCityOnlyV1=true;
})();
