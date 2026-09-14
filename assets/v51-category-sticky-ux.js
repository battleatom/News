(function(){
  'use strict';
  const VALID=new Set(['top','nfl','x','underreported','world','us','presidential','federal','legislation','nm','local','region','technology','gaming','military','entertainment','boxoffice']);
  const LABELS={'Top Stories':'top','NFL':'nfl','Top Issues':'x','Underreported':'underreported','World':'world','United States':'us','Presidential':'presidential','Federal Government':'federal','Laws & Legislation':'legislation','New Mexico':'nm','Local / Four Corners':'local','Region':'region','Technology':'technology','Gaming & Computing':'gaming','Military & War':'military','Entertainment':'entertainment','Box Office':'boxoffice'};

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
    const section=card.closest('section[data-category]');
    if(section&&VALID.has(section.dataset.category))return section.dataset.category;
    return activeCategory();
  }

  function tagRenderedCards(){
    const current=activeCategory();
    document.querySelectorAll('#news-feed section.section').forEach(sec=>{if(!VALID.has(sec.dataset.category)&&current)sec.dataset.category=current;});
    document.querySelectorAll('#news-feed .news-item').forEach(card=>{const cat=itemCategoryForCard(card);if(cat)card.dataset.category=cat;});
  }
  window.__tagRenderedCardsV51=tagRenderedCards;

  let tagQueued=false;
  function queueTag(){if(tagQueued)return;tagQueued=true;queueMicrotask(()=>{tagQueued=false;tagRenderedCards();});}

  function ensureFixedStack(){
    const container=document.querySelector('.container');
    if(!container)return null;
    let stack=container.querySelector(':scope > .v51-fixed-stack');
    if(!stack){
      stack=document.createElement('div');
      stack.className='v51-fixed-stack';
      container.insertBefore(stack,container.firstChild);
    }
    const parts=[container.querySelector(':scope > header'),container.querySelector(':scope > .toolbar'),container.querySelector(':scope > #pull-status'),container.querySelector(':scope > .markets'),container.querySelector(':scope > .tabs')].filter(Boolean);
    parts.forEach(el=>{if(el.parentElement!==stack)stack.appendChild(el);});
    let spacer=container.querySelector(':scope > .v51-fixed-spacer');
    if(!spacer){spacer=document.createElement('div');spacer.className='v51-fixed-spacer';stack.insertAdjacentElement('afterend',spacer);}
    return {stack,spacer};
  }

  function syncFixedMetrics(){
    const fixed=ensureFixedStack();
    if(!fixed)return;
    const h=Math.ceil(fixed.stack.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--v51-fixed-stack-h',h+'px');
    fixed.spacer.style.height=h+'px';
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
    ensureFixedStack();tagRenderedCards();syncFixedMetrics();scrollActiveTab('auto');
    const feed=document.getElementById('news-feed');
    if(feed)new MutationObserver(queueTag).observe(feed,{childList:true,subtree:true});
    const tabs=document.getElementById('tabs');
    if(tabs){
      new MutationObserver(()=>{scrollActiveTab('auto');syncFixedMetrics();}).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
      tabs.addEventListener('click',()=>requestAnimationFrame(()=>scrollActiveTab('smooth')),true);
    }
    const fixed=ensureFixedStack();
    if(fixed&&window.ResizeObserver)new ResizeObserver(()=>syncFixedMetrics()).observe(fixed.stack);
    window.addEventListener('resize',()=>{syncFixedMetrics();scrollActiveTab('auto')},{passive:true});
    requestAnimationFrame(()=>{syncFixedMetrics();requestAnimationFrame(syncFixedMetrics);});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
