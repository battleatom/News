(()=>{
  const root=document.getElementById('feed');
  const tabs=document.getElementById('tabs');
  if(!root)return;
  let raf=0;
  const schedule=()=>{if(raf)return;raf=requestAnimationFrame(()=>{raf=0;update()})};
  function activeTab(){return document.querySelector('#tabs .tab[aria-selected="true"]')}
  function activeKey(){return activeTab()?.dataset.category||''}
  function fixXTab(){
    const tab=tabs?.querySelector('.tab[data-category="x"]');
    if(!tab)return;
    const spans=tab.querySelectorAll(':scope > span');
    if(spans.length>=2){
      spans[0].hidden=true;
      spans[1].textContent='X';
    }
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
    fixXTab();
    const ctx=context();if(!ctx)return;
    const {cards,counter}=ctx,total=parseTotal(counter,cards.length),line=topLine();
    let index=0;
    for(let i=0;i<cards.length;i++){
      const r=cards[i].getBoundingClientRect();
      if(r.top<=line)index=i;else break;
    }
    const max=total||cards.length,current=Math.min(index+1,max),text=`${current} / ${max}`;
    if(counter.textContent!==text)counter.textContent=text;
    const badge=activeTab()?.querySelector('small');
    if(badge&&badge.textContent!==text)badge.textContent=text;
  }
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',schedule,{passive:true});
  new MutationObserver(()=>setTimeout(schedule,0)).observe(root,{childList:true,subtree:true});
  if(tabs)new MutationObserver(()=>setTimeout(schedule,0)).observe(tabs,{childList:true,subtree:true});
  document.addEventListener('v6:tabchange',()=>setTimeout(schedule,0));
  setTimeout(schedule,200);
})();
