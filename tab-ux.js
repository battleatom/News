(()=>{
  const tabs=document.getElementById("tabs");
  if(!tabs)return;

  const palette={
    top:["#0f172a","#f8fafc","rgba(15,23,42,.08)","#0f172a"],
    nfl:["#b91c1c","#fff7f7","rgba(185,28,28,.10)","#b91c1c"],
    x:["#111827","#f8fafc","rgba(17,24,39,.08)","#111827"],
    underreported:["#6d28d9","#faf7ff","rgba(109,40,217,.10)","#6d28d9"],
    world:["#0f766e","#f0fdfa","rgba(15,118,110,.10)","#0f766e"],
    us:["#1d4ed8","#eff6ff","rgba(29,78,216,.10)","#1d4ed8"],
    presidential:["#4338ca","#eef2ff","rgba(67,56,202,.10)","#4338ca"],
    federal:["#475569","#f8fafc","rgba(71,85,105,.10)","#475569"],
    legislation:["#a16207","#fffbeb","rgba(161,98,7,.11)","#a16207"],
    nm:["#c2410c","#fff7ed","rgba(194,65,12,.10)","#c2410c"],
    local:["#15803d","#f0fdf4","rgba(21,128,61,.10)","#15803d"],
    region:["#047857","#ecfdf5","rgba(4,120,87,.10)","#047857"],
    technology:["#0369a1","#f0f9ff","rgba(3,105,161,.10)","#0369a1"],
    gaming:["#7e22ce","#faf5ff","rgba(126,34,206,.10)","#7e22ce"],
    military:["#4d7c0f","#f7fee7","rgba(77,124,15,.10)","#4d7c0f"],
    entertainment:["#be185d","#fdf2f8","rgba(190,24,93,.10)","#be185d"],
    boxoffice:["#c2410c","#fff7ed","rgba(194,65,12,.10)","#c2410c"],
    bookmarks:["#a16207","#fffbeb","rgba(161,98,7,.11)","#a16207"],
    admin:["#334155","#f8fafc","rgba(51,65,85,.10)","#334155"]
  };

  const style=document.createElement("style");
  style.id="v531-tab-ux";
  style.textContent=`
    .tabs{scroll-behavior:smooth;scroll-snap-type:x proximity;overscroll-behavior-x:contain}
    .tab{scroll-snap-align:center;position:relative;transition:background-color .18s ease,border-color .18s ease,color .18s ease,box-shadow .18s ease,transform .12s ease}
    .tab:active{transform:scale(.97)}
    .tab[data-v531-color]{border-color:var(--tab-border);background:var(--tab-bg);color:var(--tab-color)}
    .tab[data-v531-color]:hover{border-color:var(--tab-accent);color:var(--tab-accent)}
    .tab[data-v531-color][aria-selected="true"]{background:var(--tab-accent);border-color:var(--tab-accent);color:#fff;box-shadow:0 5px 15px var(--tab-shadow)}
    .tab[data-v531-color][aria-selected="true"] small{opacity:.82}
    @media (prefers-reduced-motion:reduce){.tabs{scroll-behavior:auto}.tab{transition:none}}
  `;
  document.head.appendChild(style);

  function decorate(){
    tabs.querySelectorAll(".tab[data-category]").forEach(tab=>{
      const p=palette[tab.dataset.category]||palette.top;
      tab.dataset.v531Color="1";
      tab.style.setProperty("--tab-accent",p[0]);
      tab.style.setProperty("--tab-bg",p[1]);
      tab.style.setProperty("--tab-border",p[2]);
      tab.style.setProperty("--tab-color",p[3]);
      tab.style.setProperty("--tab-shadow",p[2].replace(/\.10\)/,".28)").replace(/\.11\)/,".28)").replace(/\.08\)/,".26)"));
    });
  }

  function centerActive(behavior="smooth"){
    const active=tabs.querySelector('.tab[aria-selected="true"]');
    if(!active)return;
    const target=active.offsetLeft-(tabs.clientWidth-active.offsetWidth)/2;
    const max=Math.max(0,tabs.scrollWidth-tabs.clientWidth);
    tabs.scrollTo({left:Math.max(0,Math.min(max,target)),behavior});
  }

  function nudgeAdmin(){
    const active=tabs.querySelector('.tab[aria-selected="true"]');
    if(active?.dataset.category!=="admin")return;
    const feed=document.getElementById("feed");
    if(!feed)return;
    const marker=document.createComment("admin-ops-render");
    feed.appendChild(marker);
    requestAnimationFrame(()=>marker.remove());
  }

  let previousSelected="";
  function sync(behavior="smooth"){
    decorate();
    const active=tabs.querySelector('.tab[aria-selected="true"]');
    const key=active?.dataset.category||"";
    if(key&&key!==previousSelected){
      previousSelected=key;
      requestAnimationFrame(()=>centerActive(behavior));
      if(key==="admin")setTimeout(nudgeAdmin,100);
    }
  }

  let resizeTimer=0;
  window.addEventListener("resize",()=>{
    clearTimeout(resizeTimer);
    resizeTimer=setTimeout(()=>centerActive("smooth"),90);
  },{passive:true});
  window.addEventListener("orientationchange",()=>setTimeout(()=>centerActive("smooth"),180),{passive:true});

  tabs.addEventListener("click",event=>{
    const button=event.target.closest(".tab[data-category]");
    if(!button)return;
    const same=button.getAttribute("aria-selected")==="true";
    const y=window.scrollY;
    if(same){
      requestAnimationFrame(()=>requestAnimationFrame(()=>window.scrollTo({top:y,left:0,behavior:"auto"})));
    }
    setTimeout(()=>centerActive("smooth"),20);
    if(button.dataset.category==="admin")setTimeout(nudgeAdmin,140);
  },true);

  new MutationObserver(()=>sync("smooth")).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:["aria-selected","class"]});
  sync("auto");
})();