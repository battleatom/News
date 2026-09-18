(()=>{
  const tabs=document.getElementById("tabs");
  const root=document.getElementById("feed");
  if(!tabs||!root)return;

  const X_SLOTS=["x-health","x-technology","x-celebrities","x-world","x-politics","x-entertainment","x-sports","x-business","x-gaming","x-science"];
  const corrected=new Map();
  let syncing=false;

  const norm=value=>String(value||"").toLowerCase().replace(/[^a-z0-9]+/g," ").replace(/\s+/g," ").trim();
  const xSlotId=(story,index)=>{
    const direct=String(story?.source_id||story?.sourceId||story?.x_slot||story?.xSlot||"").trim().toLowerCase().replace(/_/g,"-");
    if(direct){
      for(const id of X_SLOTS)if(direct===id||direct.startsWith(`${id}-`))return id;
    }
    const topic=norm(story?.x_topic||story?.xTopic||story?.topic||story?.slot||"");
    const aliases={
      "x-health":["health","medical"],
      "x-technology":["technology","artificial intelligence"," ai "],
      "x-celebrities":["celebrit","public figures"],
      "x-world":["world","international"],
      "x-politics":["politics","government"],
      "x-entertainment":["entertainment"],
      "x-sports":["sports"],
      "x-business":["business","economy"],
      "x-gaming":["gaming"],
      "x-science":["science"]
    };
    if(topic){for(const[id,terms]of Object.entries(aliases))if(terms.some(term=>topic.includes(term.trim())))return id;}
    return X_SLOTS[index%X_SLOTS.length];
  };

  const isSuppressed=(story,pools,category)=>{
    const url=norm(story?.url),title=norm(story?.title),source=norm(story?.source);
    const same=(record,requireCategory)=>{
      if(!record||record.serverCount)return false;
      if(requireCategory&&norm(record.category||record.tab)!==norm(category))return false;
      const ru=norm(record.url_key||record.urlKey||record.url);
      if(ru&&url&&ru===url)return true;
      const rt=norm(record.title_key||record.titleKey||record.title),rs=norm(record.source_key||record.sourceKey||record.source);
      return Boolean(rt&&rs&&rt===title&&rs===source);
    };
    return (pools.D||[]).some(r=>same(r,false))||(pools.NR||[]).some(r=>same(r,true))||(pools.NW||[]).some(r=>same(r,true));
  };

  function apply(){
    for(const[key,count]of corrected){
      const small=tabs.querySelector(`.tab[data-category="${CSS.escape(key)}"] small`);
      if(small&&small.textContent!==String(count))small.textContent=String(count);
    }
  }

  function syncActiveFromRendered(){
    const active=tabs.querySelector('.tab[aria-selected="true"][data-category]');
    if(!active)return;
    const key=active.dataset.category;
    const stat=root.querySelector(".section-stats span");
    const match=stat?.textContent?.match(/(\d+)\s+of\s+(\d+)/i);
    if(match){
      corrected.set(key,key==="x"?Number(match[1]):Number(match[2]));
      apply();
      return;
    }
    if(!["nfl","boxoffice","admin"].includes(key)){
      const cards=root.querySelectorAll(`.story-card[data-category="${CSS.escape(key)}"]`).length;
      if(cards||key==="bookmarks"){
        corrected.set(key,cards);
        apply();
      }
    }
  }

  async function syncAll(){
    if(syncing)return;
    syncing=true;
    try{
      const [feedResp,feedbackResp]=await Promise.all([
        fetch(`feed.json?tabcounts=${Date.now()}`,{cache:"no-store"}),
        fetch(`/api/feedback?tabcounts=${Date.now()}`,{cache:"no-store"}).catch(()=>null)
      ]);
      if(!feedResp.ok)return;
      const feed=await feedResp.json();
      let pools={D:[],NR:[],NW:[]};
      if(feedbackResp?.ok){const data=await feedbackResp.json();pools={...pools,...(data?.pools||{})};}
      for(const key of Object.keys(feed?.categories||{})){
        if(["nfl","boxoffice"].includes(key))continue;
        let rows=[...(feed?.stories?.[key]||[]),...(feed?.reserves?.[key]||[])].filter(story=>!isSuppressed(story,pools,key));
        if(key==="x"){
          const slots=new Set(rows.map((story,index)=>xSlotId(story,index)));
          corrected.set(key,X_SLOTS.filter(id=>slots.has(id)).length);
        }else corrected.set(key,rows.length);
      }
      try{corrected.set("bookmarks",JSON.parse(localStorage.getItem("underreported-v6-bookmarks")||"[]").length)}catch{}
      apply();
      syncActiveFromRendered();
    }catch(error){console.warn("Tab count sync unavailable",error)}finally{syncing=false;}
  }

  let timer=0;
  const schedule=()=>{clearTimeout(timer);timer=setTimeout(()=>{apply();syncActiveFromRendered();},0)};
  new MutationObserver(schedule).observe(tabs,{childList:true,subtree:true,characterData:true});
  new MutationObserver(schedule).observe(root,{childList:true,subtree:true,characterData:true});
  root.addEventListener("click",event=>{
    if(event.target.closest("[data-feedback]"))setTimeout(syncAll,500);
    if(event.target.closest("[data-bookmark]"))setTimeout(syncAll,50);
  },true);
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)syncAll()});
  setInterval(syncAll,60000);
  setTimeout(syncAll,100);
})();
