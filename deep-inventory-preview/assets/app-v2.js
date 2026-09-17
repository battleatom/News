(function(){
  'use strict';
  let navQueued=false,feedQueued=false;

  function sectionDefs(){return typeof sections!=='undefined'&&Array.isArray(sections)?sections:[];}
  function currentActive(){return typeof active!=='undefined'?active:'top';}

  function enhanceTabs(){
    navQueued=false;
    const tabs=document.getElementById('tabs');if(!tabs)return;
    document.getElementById('more-tab-v2')?.remove();
    document.getElementById('more-menu-v2')?.remove();
    const defs=sectionDefs();
    const regular=[...tabs.querySelectorAll(':scope > .tab')].filter(b=>b.id!=='bookmarks-tab');
    regular.forEach((b,i)=>{
      const key=defs[i]?.[0]||'';
      if(!key)return;
      b.dataset.navKey=key;
      b.removeAttribute('data-nav-secondary');
      b.setAttribute('aria-current',key===currentActive()?'page':'false');
      b.style.removeProperty('order');
    });
    const bookmark=document.getElementById('bookmarks-tab');
    if(bookmark){
      bookmark.dataset.navKey='bookmarks';
      bookmark.removeAttribute('data-nav-secondary');
      bookmark.style.removeProperty('order');
      bookmark.setAttribute('aria-current',currentActive()==='bookmarks'?'page':'false');
    }
    const activeTab=tabs.querySelector('.tab.active');
    if(activeTab&&window.innerWidth<=760){
      requestAnimationFrame(()=>activeTab.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'}));
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
    root.querySelectorAll('.lead-story-v2').forEach(card=>card.classList.remove('lead-story-v2'));
    root.querySelectorAll('.news-item-v2-kicker').forEach(kicker=>kicker.remove());
    addUnderreportedSignal(root);
    root.querySelectorAll('.related-coverage[data-source-count]').forEach(box=>{
      const strong=box.querySelector('strong');
      const expected=`Coverage · ${box.dataset.sourceCount} sources`;
      if(strong&&strong.textContent!==expected)strong.textContent=expected;
    });
  }
  function queueFeed(){if(feedQueued)return;feedQueued=true;requestAnimationFrame(decorateFeed);}

  async function loadHealth(){
    const panel=document.getElementById('pull-stats-ui');if(!panel)return;
    try{
      const r=await fetch('refresh-health.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)return;
      const d=await r.json();panel.dataset.health=d.status||'unknown';
      if(d.status==='degraded'){
        const strong=panel.querySelector('strong');if(strong)strong.textContent='⚠ Feed refresh delayed';
        panel.title=d.message||'The last automated collection did not complete successfully; the previous feed is being served.';
      }
    }catch(e){}
  }

  function wrapTabBuilder(fn){
    if(typeof fn!=='function'||fn.__v2)return fn;
    const wrapped=function(){const out=fn.apply(this,arguments);queueNav();return out;};
    wrapped.__v2=true;wrapped.__v2Original=fn;return wrapped;
  }
  function wrapRenderer(fn){
    if(typeof fn!=='function'||fn.__v2)return fn;
    const wrapped=function(){const out=fn.apply(this,arguments);queueNav();queueFeed();return out;};
    wrapped.__v2=true;wrapped.__v2Original=fn;return wrapped;
  }

  function installHooks(){
    if(typeof canonicalBuildTabs==='function')canonicalBuildTabs=wrapTabBuilder(canonicalBuildTabs);
    if(typeof buildTabs==='function')buildTabs=wrapTabBuilder(buildTabs);
    if(typeof canonicalRender==='function')canonicalRender=wrapRenderer(canonicalRender);
    if(typeof render==='function')render=wrapRenderer(render);
  }

  function start(){
    installHooks();
    const tabs=document.getElementById('tabs');if(tabs)new MutationObserver(queueNav).observe(tabs,{childList:true});
    const root=document.getElementById('news-feed');
    // Rendering already queues decoration directly. Observe only top-level card-list
    // changes as a safety net; nested badge/text mutations no longer retrigger work.
    if(root)new MutationObserver(queueFeed).observe(root,{childList:true});
    queueNav();queueFeed();loadHealth();
    window.__underreportedV2=true;
    window.__underreportedV28Optimized=true;
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
