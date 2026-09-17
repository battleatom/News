(()=>{
  const root=document.getElementById('feed');if(!root)return;
  let observed=null,loading=false;
  const io=new IntersectionObserver(entries=>{
    for(const entry of entries){
      if(!entry.isIntersecting||entry.target!==observed||loading)continue;
      const button=root.querySelector('[data-infinite-sentinel] [data-action="load-more"]');
      if(!button||button.disabled)continue;
      loading=true;
      io.unobserve(entry.target);
      requestAnimationFrame(()=>{button.click();setTimeout(()=>{loading=false;sync()},0)});
    }
  },{root:null,rootMargin:'0px',threshold:0.15});
  function cards(){
    const nfl=root.querySelector('.nfl-news-list');
    if(nfl)return[...nfl.querySelectorAll('.story-card')];
    const list=root.querySelector('.story-list');
    return list?[...list.querySelectorAll('.story-card')]:[];
  }
  function sync(){
    const sentinel=root.querySelector('[data-infinite-sentinel]');
    const rows=cards();
    const next=sentinel&&rows.length>3?rows[Math.max(0,rows.length-4)]:null;
    if(next===observed)return;
    if(observed)io.unobserve(observed);
    observed=next;
    if(observed)io.observe(observed);
  }
  new MutationObserver(()=>queueMicrotask(sync)).observe(root,{childList:true,subtree:true});
  sync();
})();
