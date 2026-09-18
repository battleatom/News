(()=>{
  const root=document.getElementById('feed');
  const tabs=document.getElementById('tabs');
  if(!root)return;
  let raf=0;
  const poolTotals=new Map();
  const schedule=()=>{if(raf)return;raf=requestAnimationFrame(()=>{raf=0;update()})};
  function activeTab(){return document.querySelector('#tabs .tab[aria-selected="true"]')}
  function activeKey(){return activeTab()?.dataset.category||''}
  function fixXTab(){
    const tab=tabs?.querySelector('.tab[data-category="x"]');
    if(!tab)return;
    const spans=tab.querySelectorAll(':scope > span');
    if(spans.length>=2){spans[0].hidden=true;spans[1].textContent='X'}
  }
  async function loadPoolTotals(){
    try{
      const response=await fetch(`feed.json?ts=${Date.now()}`,{cache:'no-store'});
      if(!response.ok)return;
      const feed=await response.json();
      for(const key of Object.keys(feed.categories||{})){
        const rows=[...(feed.stories?.[key]||[]),...(feed.reserves?.[key]||[])];
        if(key==='x')poolTotals.set(key,new Set(rows.map(row=>row.source_id).filter(Boolean)).size);
        else poolTotals.set(key,rows.length);
      }
      syncTabTotals();
    }catch{}
  }
  function syncTabTotals(){
    if(!tabs)return;
    const active=activeKey();
    for(const tab of tabs.querySelectorAll('.tab[data-category]')){
      const key=tab.dataset.category||'';
      if(key===active||key==='boxoffice'||key==='bookmarks'||key==='admin')continue;
      const total=poolTotals.get(key);
      const badge=tab.querySelector('small');
      if(badge&&Number.isFinite(total)&&badge.textContent!==String(total))badge.textContent=String(total);
    }
    fixXTab();
  }
  function topLine(){
    const shell=document.getElementById('app-shell');
    if(!shell)return 16;
    const pos=getComputedStyle(shell).position;
    if(pos==='sticky'||pos==='fixed')return Math.max(16,Math.min(innerHeight*.45,shell.getBoundingClientRect().bottom+8));
    return 16;
  }
  function parseTotal(el,fallback){
    if(!el)return fallback;
    if(el.dataset.positionTotal)return Number(el.dataset.positionTotal)||fallback;
    const nums=(el.textContent.match(/\d+/g)||[]).map(Number);
    const total=nums.length?nums[nums.length-1]:fallback;
    el.dataset.positionTotal=String(total||fallback||0);
    return total||fallback;
  }
  function context(){
    const key=activeKey();
    if(key==='admin')return null;
    if(key==='nfl'){
      const cards=[...root.querySelectorAll('.nfl-news-list .story-card')];
      const counter=root.querySelector('.nfl-news-head span');
      return cards.length&&counter?{cards,counter}:null;
    }
    if(key==='boxoffice'){
      const cards=[...root.querySelectorAll('.movie-card')];
      const counter=root.querySelector('.section-stats span');
      return cards.length&&counter?{cards,counter}:null;
    }
    const cards=[...root.querySelectorAll('.story-list .story-card')];
    const counter=root.querySelector('.section-stats span');
    return cards.length&&counter?{cards,counter}:null;
  }
  function update(){
    syncTabTotals();
    const ctx=context();if(!ctx)return;
    const key=activeKey(),{cards,counter}=ctx,total=key==='x'?cards.length:parseTotal(counter,cards.length),line=topLine();
    let index=0;
    for(let i=0;i<cards.length;i++){
      const r=cards[i].getBoundingClientRect();
      if(r.top<=line)index=i;else break;
    }
    const max=total||cards.length,current=Math.min(index+1,max),text=`${current} / ${max}`;
    if(counter.textContent!==text)counter.textContent=text;
    if(key&&key!=='boxoffice')poolTotals.set(key,max);
    const badge=activeTab()?.querySelector('small');
    const badgeText=key==='x'?String(max):text;
    if(badge&&badge.textContent!==badgeText)badge.textContent=badgeText;
  }
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',schedule,{passive:true});
  new MutationObserver(()=>setTimeout(schedule,0)).observe(root,{childList:true,subtree:true});
  if(tabs)new MutationObserver(()=>setTimeout(schedule,0)).observe(tabs,{childList:true,subtree:true});
  document.addEventListener('v6:tabchange',()=>setTimeout(schedule,0));
  loadPoolTotals();
  setTimeout(schedule,200);
})();
