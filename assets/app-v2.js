(function(){
  'use strict';
  const PRIMARY=new Set(['top','underreported','world','us','region','x']);
  let navQueued=false,feedQueued=false;

  function sectionDefs(){return typeof sections!=='undefined'&&Array.isArray(sections)?sections:[];}
  function currentActive(){return typeof active!=='undefined'?active:'top';}
  function cleanLabel(label){return String(label||'').replace(/^\S+\s+/,'').trim();}

  function closeMore(){
    const menu=document.getElementById('more-menu-v2'),btn=document.getElementById('more-tab-v2');
    if(menu)menu.classList.remove('open');
    if(btn)btn.setAttribute('aria-expanded','false');
  }

  function activateKey(key){
    closeMore();
    if(key==='bookmarks'){
      const b=document.getElementById('bookmarks-tab');if(b)b.click();
      return;
    }
    if(typeof active==='undefined')return;
    active=key;
    try{localStorage.setItem('underreported-active-tab',active);}catch(e){}
    if(typeof buildTabs==='function')buildTabs();
    if(typeof render==='function'&&typeof allItems!=='undefined')render(allItems);
  }

  function enhanceTabs(){
    navQueued=false;
    const tabs=document.getElementById('tabs');if(!tabs)return;
    const defs=sectionDefs();
    const regular=[...tabs.querySelectorAll(':scope > .tab')].filter(b=>b.id!=='more-tab-v2'&&b.id!=='bookmarks-tab');
    regular.forEach((b,i)=>{
      const key=defs[i]?.[0]||'';
      if(!key)return;
      b.dataset.navKey=key;
      b.dataset.navSecondary=PRIMARY.has(key)?'false':'true';
      b.setAttribute('aria-current',key===currentActive()?'page':'false');
    });
    const bookmark=document.getElementById('bookmarks-tab');
    if(bookmark){bookmark.dataset.navKey='bookmarks';bookmark.dataset.navSecondary='true';}

    let more=document.getElementById('more-tab-v2');
    if(!more){
      more=document.createElement('button');more.id='more-tab-v2';more.type='button';more.className='tab';more.setAttribute('aria-haspopup','menu');more.setAttribute('aria-expanded','false');
      more.addEventListener('click',e=>{e.stopPropagation();const menu=document.getElementById('more-menu-v2');if(!menu)return;const open=!menu.classList.contains('open');menu.classList.toggle('open',open);more.setAttribute('aria-expanded',String(open));});
      tabs.appendChild(more);
    }
    let menu=document.getElementById('more-menu-v2');
    if(!menu){menu=document.createElement('div');menu.id='more-menu-v2';menu.className='more-menu-v2';menu.setAttribute('role','menu');tabs.appendChild(menu);}

    const secondary=defs.filter(d=>!PRIMARY.has(d[0]));
    const activeKey=currentActive();
    const activeDef=defs.find(d=>d[0]===activeKey);
    more.textContent=!PRIMARY.has(activeKey)&&activeKey!=='bookmarks'&&activeDef?`More · ${cleanLabel(activeDef[1])}`:'More';
    more.classList.toggle('active',!PRIMARY.has(activeKey)||activeKey==='bookmarks');
    menu.innerHTML='';
    secondary.forEach(([key,label])=>{
      const b=document.createElement('button');b.type='button';b.setAttribute('role','menuitem');b.dataset.navKey=key;b.textContent=label;b.classList.toggle('active',key===activeKey);b.addEventListener('click',()=>activateKey(key));menu.appendChild(b);
    });
    if(bookmark){
      const b=document.createElement('button');b.type='button';b.setAttribute('role','menuitem');b.dataset.navKey='bookmarks';b.textContent=bookmark.textContent||'🔖 Bookmarks';b.classList.toggle('active',activeKey==='bookmarks');b.addEventListener('click',()=>activateKey('bookmarks'));menu.appendChild(b);
    }
  }

  function queueNav(){if(navQueued)return;navQueued=true;queueMicrotask(enhanceTabs);}

  function matchingFeedItem(card){
    if(typeof allItems==='undefined')return null;
    const title=(card.querySelector('h3 a')?.textContent||'').replace(/^\d+\.\s*/,'').trim();
    if(!title)return null;
    return allItems.find(x=>(x.querySelector('title')?.textContent||'').trim()===title)||null;
  }

  function addUnderreportedSignal(root){
    if(currentActive()!=='underreported')return;
    root.querySelectorAll('.underreported-item').forEach(card=>{
      if(card.querySelector('.underreported-signal-v2'))return;
      const item=matchingFeedItem(card);if(!item)return;
      const related=[...item.querySelectorAll('related > article')];
      const stored=Number(item.querySelector('underreportedScore')?.textContent||0);
      const sources=Number(item.querySelector('supportingSourceCount')?.textContent||0)||new Set(related.map(r=>(r.querySelector('source')?.textContent||'').trim().toLowerCase()).filter(Boolean)).size;
      const score=stored||Math.max(50,Math.min(96,96-sources*10));
      const chip=document.createElement('span');chip.className='underreported-signal-v2';chip.textContent=`Underreported signal ${score}/100 · ${sources} supporting source${sources===1?'':'s'}`;
      chip.title='Heuristic only: a higher score means fewer distinct supporting sources were found by the related-news search.';
      chip.setAttribute('aria-label',chip.textContent+'. Heuristic only; higher means less supporting coverage was found.');
      const topline=card.querySelector('.underreported-topline')||card;
      topline.appendChild(chip);
    });
  }

  function decorateFeed(){
    feedQueued=false;
    const key=currentActive();
    document.body.dataset.activeTab=key;
    const root=document.getElementById('news-feed');if(!root)return;
    root.querySelectorAll('.lead-story-v2').forEach(x=>x.classList.remove('lead-story-v2'));
    root.querySelectorAll('.news-item-v2-kicker').forEach(x=>x.remove());
    if(key==='top'){
      const first=root.querySelector('.news-item');
      if(first){
        first.classList.add('lead-story-v2');
        const kicker=document.createElement('div');kicker.className='news-item-v2-kicker';kicker.textContent='Lead story';
        const target=first.querySelector('.bookmark-btn')||first.querySelector('h3');
        if(target)target.insertAdjacentElement('beforebegin',kicker);
      }
    }
    addUnderreportedSignal(root);
    root.querySelectorAll('.related-coverage[data-source-count]').forEach(box=>{
      const strong=box.querySelector('strong');if(strong)strong.textContent=`Coverage · ${box.dataset.sourceCount} sources`;
    });
  }
  function queueFeed(){if(feedQueued)return;feedQueued=true;requestAnimationFrame(decorateFeed);}

  async function loadHealth(){
    const panel=document.getElementById('pull-stats-ui');if(!panel)return;
    try{
      const r=await fetch('refresh-health.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)return;
      const d=await r.json();panel.dataset.health=d.status||'unknown';
      if(d.status==='degraded'){
        const strong=panel.querySelector('strong');if(strong)strong.textContent='⚠ Feed refresh degraded';
        panel.title=d.message||'The last automated collection did not complete successfully; the previous feed is being served.';
      }
    }catch(e){}
  }

  function installHooks(){
    if(typeof buildTabs==='function'&&!buildTabs.__v2){
      const prior=buildTabs;
      const wrapped=function(){const out=prior.apply(this,arguments);queueNav();return out;};wrapped.__v2=true;buildTabs=wrapped;
    }
    if(typeof render==='function'&&!render.__v2){
      const prior=render;
      const wrapped=function(){const out=prior.apply(this,arguments);queueNav();queueFeed();return out;};wrapped.__v2=true;render=wrapped;
    }
  }

  function start(){
    installHooks();
    const tabs=document.getElementById('tabs');if(tabs)new MutationObserver(queueNav).observe(tabs,{childList:true});
    const root=document.getElementById('news-feed');if(root)new MutationObserver(queueFeed).observe(root,{childList:true,subtree:true});
    document.addEventListener('click',e=>{if(!e.target.closest('#more-tab-v2')&&!e.target.closest('#more-menu-v2'))closeMore();});
    document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMore();});
    queueNav();queueFeed();loadHealth();
    window.__underreportedV2=true;
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
