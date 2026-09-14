(function(){
  'use strict';
  const VALID=new Set(['top','nfl','x','underreported','world','us','presidential','federal','legislation','nm','local','region','technology','gaming','military','entertainment','boxoffice']);
  const LABELS={
    'Top Stories':'top','NFL':'nfl','Top Issues':'x','Underreported':'underreported','World':'world','United States':'us',
    'Presidential':'presidential','Federal Government':'federal','Laws & Legislation':'legislation','New Mexico':'nm',
    'Local / Four Corners':'local','Region':'region','Technology':'technology','Gaming & Computing':'gaming','Military & War':'military',
    'Entertainment':'entertainment','Box Office':'boxoffice'
  };

  function activeCategory(){
    try{if(typeof active!=='undefined'&&VALID.has(active))return active;}catch(e){}
    const tab=document.querySelector('#tabs .tab.active');
    if(!tab)return '';
    const text=(tab.textContent||'').replace(/^[^A-Za-z0-9]+/,'').replace(/\s*\(\d+\)\s*$/,'').trim();
    for(const [label,key] of Object.entries(LABELS))if(text===label||text.includes(label))return key;
    return '';
  }

  function itemCategoryForCard(card){
    if(VALID.has(card.dataset.category))return card.dataset.category;
    if(card.classList.contains('movie-card'))return 'boxoffice';
    if(card.classList.contains('underreported-item'))return 'underreported';
    if(card.classList.contains('nfl-game-card'))return 'nfl';
    if(card.closest('.bookmark-section')){
      const a=card.querySelector('h3 a[href]');
      const title=(a?.textContent||'').replace(/^\d+\.\s*/,'').trim().toLowerCase();
      try{
        if(typeof allItems!=='undefined'){
          const item=allItems.find(x=>(x.querySelector('title')?.textContent||'').trim().toLowerCase()===title);
          const cat=(item?.querySelector('category')?.textContent||'').trim();
          if(VALID.has(cat))return cat;
        }
      }catch(e){}
      return '';
    }
    const section=card.closest('section[data-category]');
    if(section&&VALID.has(section.dataset.category))return section.dataset.category;
    return activeCategory();
  }

  function tagRenderedCards(){
    const current=activeCategory();
    document.querySelectorAll('#news-feed section.section').forEach(sec=>{
      if(!VALID.has(sec.dataset.category)&&current)sec.dataset.category=current;
    });
    document.querySelectorAll('#news-feed .news-item').forEach(card=>{
      const cat=itemCategoryForCard(card);
      if(cat)card.dataset.category=cat;
    });
  }
  window.__tagRenderedCardsV51=tagRenderedCards;

  let tagQueued=false;
  function queueTag(){if(tagQueued)return;tagQueued=true;queueMicrotask(()=>{tagQueued=false;tagRenderedCards();});}

  function syncStickyMetrics(){
    const root=document.documentElement;
    const header=document.querySelector('body>header, header');
    const toolbar=document.querySelector('.toolbar');
    const status=document.getElementById('pull-status');
    const markets=document.querySelector('.markets');
    root.style.setProperty('--v51-header-h',(header?.offsetHeight||0)+'px');
    root.style.setProperty('--v51-toolbar-h',(toolbar?.offsetHeight||0)+'px');
    root.style.setProperty('--v51-status-h',(status?.offsetHeight||0)+'px');
    root.style.setProperty('--v51-markets-h',(markets?.offsetHeight||0)+'px');
  }

  function scrollActiveTab(behavior='auto'){
    const tabs=document.getElementById('tabs');
    const tab=tabs?.querySelector('.tab.active');
    if(!tabs||!tab)return;
    const left=tab.offsetLeft-(tabs.clientWidth-tab.offsetWidth)/2;
    const max=Math.max(0,tabs.scrollWidth-tabs.clientWidth);
    const target=Math.max(0,Math.min(max,left));
    if(Math.abs(tabs.scrollLeft-target)>8)tabs.scrollTo({left:target,behavior});
  }

  function start(){
    tagRenderedCards();syncStickyMetrics();scrollActiveTab('auto');
    const feed=document.getElementById('news-feed');
    if(feed)new MutationObserver(queueTag).observe(feed,{childList:true,subtree:true});
    const tabs=document.getElementById('tabs');
    if(tabs){
      new MutationObserver(()=>{scrollActiveTab('auto');syncStickyMetrics();}).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
      tabs.addEventListener('click',()=>requestAnimationFrame(()=>scrollActiveTab('smooth')),true);
    }
    const ro=new ResizeObserver(()=>syncStickyMetrics());
    [document.querySelector('body>header, header'),document.querySelector('.toolbar'),document.getElementById('pull-status'),document.querySelector('.markets'),tabs].filter(Boolean).forEach(el=>ro.observe(el));
    window.addEventListener('resize',()=>{syncStickyMetrics();scrollActiveTab('auto')},{passive:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
