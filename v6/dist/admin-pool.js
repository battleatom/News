(()=>{
  const tabs=document.getElementById('tabs'),feed=document.getElementById('feed');
  if(!tabs||!feed)return;
  const labelToKey={
    'Top Stories':'top','NFL':'nfl','X':'x','Underreported':'underreported','World':'world',
    'United States':'us','US':'us','Presidential':'presidential','Federal Government':'federal','Federal':'federal',
    'Laws & Legislation':'legislation','Legislation':'legislation','New Mexico':'nm','Local':'local','Region':'region',
    'Technology':'technology','Gaming & Computing':'gaming','Gaming':'gaming','Military & War':'military','Military':'military',
    'Entertainment':'entertainment','Box Office':'boxoffice'
  };
  let busy=false;
  const active=()=>!!tabs.querySelector('.tab[data-category="admin"][aria-selected="true"]');
  async function status(){
    try{const r=await fetch(`status.json?ts=${Date.now()}`,{cache:'no-store'});if(!r.ok)return null;return r.json()}catch{return null}
  }
  function inventoryRoot(){
    const wrap=feed.firstElementChild;if(!wrap)return null;
    const title=[...wrap.querySelectorAll('div')].find(el=>el.children.length===0&&el.textContent.trim()==='Category Inventory');
    return title?.parentElement?.children?.[1]||null;
  }
  async function apply(){
    if(busy||!active())return;busy=true;
    try{
      const data=await status();if(!data)return;
      const grid=inventoryRoot();if(!grid)return;
      const live=data.categoryCounts||{},reserve=data.reserveCounts||{};
      for(const card of [...grid.children]){
        const label=card.children?.[0]?.textContent?.trim()||'';
        const key=labelToKey[label];if(!key||key==='boxoffice')continue;
        const liveCount=Number(live[key]||0),backupCount=Number(reserve[key]||0),total=liveCount+backupCount;
        const strong=card.querySelector('strong');if(!strong)continue;
        strong.innerHTML=`<span style="color:var(--good)">${total}</span><span style="color:var(--muted);font-weight:800;margin:0 5px">/</span><span style="color:#2563eb">${backupCount}</span>`;
        strong.style.fontSize='1.45rem';
        strong.style.lineHeight='1';
        strong.style.letterSpacing='-.02em';
        let sub=card.querySelector('[data-pool-breakdown]');
        if(!sub){sub=document.createElement('div');sub.dataset.poolBreakdown='1';card.appendChild(sub)}
        sub.style.cssText='font-size:.54rem;color:var(--muted);margin-top:5px;line-height:1.25;font-weight:750';
        sub.textContent=`${liveCount} live`;
      }
    }finally{busy=false}
  }
  const schedule=()=>{if(active())setTimeout(apply,80)};
  new MutationObserver(schedule).observe(feed,{childList:true,subtree:false});
  tabs.addEventListener('click',e=>{if(e.target.closest('.tab[data-category="admin"]'))setTimeout(apply,180)},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')schedule()});
  setInterval(()=>{if(active())apply()},30000);
})();