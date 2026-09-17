(()=>{
  const root=document.getElementById('feed');
  if(!root)return;
  let raf=0;
  const schedule=()=>{if(raf)return;raf=requestAnimationFrame(()=>{raf=0;update()})};
  function activeKey(){return document.querySelector('#tabs .tab[aria-selected="true"]')?.dataset.category||''}
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
    const ctx=context();if(!ctx)return;
    const {cards,counter}=ctx,total=parseTotal(ctx.counter,cards.length),line=topLine();
    let index=0;
    for(let i=0;i<cards.length;i++){
      const r=cards[i].getBoundingClientRect();
      if(r.top<=line)index=i;else break;
    }
    const text=`${Math.min(index+1,total||cards.length)} / ${total||cards.length}`;
    if(counter.textContent!==text)counter.textContent=text;
  }
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',schedule,{passive:true});
  new MutationObserver(()=>setTimeout(schedule,0)).observe(root,{childList:true,subtree:true});
  document.addEventListener('v6:tabchange',()=>setTimeout(schedule,0));
  setTimeout(schedule,200);
})();
