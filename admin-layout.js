(()=>{
  const tabs=document.getElementById('tabs'),feed=document.getElementById('feed');
  if(!tabs||!feed)return;
  const style=document.createElement('style');
  style.id='admin-source-health-layout';
  style.textContent=`
    #admin-source-health-block{margin-top:2px}
    #admin-source-health-block>.admin-source-health-grid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;column-gap:18px!important;row-gap:0!important}
    #admin-source-health-block>.admin-source-health-grid>div{min-width:0}
    @media(max-width:760px){#admin-source-health-block>.admin-source-health-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;column-gap:10px!important}#admin-source-health-block>.admin-source-health-grid>div{padding-top:9px!important;padding-bottom:9px!important}#admin-source-health-block>.admin-source-health-grid>div>div:nth-child(2)>div:first-child{font-size:.67rem!important}}
  `;
  document.head.appendChild(style);
  const adminActive=()=>!!tabs.querySelector('.tab[data-category="admin"][aria-selected="true"]');
  function apply(){
    if(!adminActive())return;
    const wrap=feed.firstElementChild;if(!wrap)return;
    const heading=[...wrap.querySelectorAll('div')].find(el=>el.children.length===0&&el.textContent.trim()==='Source Health');
    if(!heading)return;
    const block=heading.parentElement;if(!block)return;
    block.id='admin-source-health-block';
    const grid=[...block.children].find(el=>el!==heading&&el.children.length>2)||block.children[1];
    if(grid)grid.classList.add('admin-source-health-grid');
    if(wrap.lastElementChild!==block)wrap.appendChild(block);
  }
  const schedule=()=>{if(adminActive())setTimeout(apply,80)};
  new MutationObserver(schedule).observe(feed,{childList:true,subtree:false});
  new MutationObserver(schedule).observe(tabs,{subtree:true,attributes:true,attributeFilter:['aria-selected'],childList:true});
  tabs.addEventListener('click',e=>{if(e.target.closest('.tab[data-category="admin"]'))setTimeout(apply,160)},true);
  document.addEventListener('v6:tabchange',e=>{if(e.detail?.category==='admin')schedule()});
  setInterval(()=>{if(adminActive())apply()},2000);
})();