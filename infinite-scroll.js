(()=>{
  const root=document.getElementById('feed');if(!root)return;
  let observed=null;
  const io=new IntersectionObserver(entries=>{
    for(const entry of entries){
      if(!entry.isIntersecting)continue;
      const sentinel=entry.target;
      io.unobserve(sentinel);
      const button=sentinel.querySelector('[data-action="load-more"]');
      if(button&&!button.disabled)requestAnimationFrame(()=>button.click());
    }
  },{root:null,rootMargin:'900px 0px',threshold:0.01});
  function sync(){
    const next=root.querySelector('[data-infinite-sentinel]');
    if(next===observed)return;
    if(observed)io.unobserve(observed);
    observed=next||null;
    if(observed)io.observe(observed);
  }
  new MutationObserver(sync).observe(root,{childList:true,subtree:true});
  sync();
})();
