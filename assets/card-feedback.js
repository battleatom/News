(()=>{
  'use strict';
  const API_URL='https://bkcrgfkhgjypvzwubwrh.supabase.co/functions/v1/news-feedback';
  const REASONS=['D','NR','NW'];
  const remotePools={D:[],NR:[],NW:[]};
  let decorating=false;
  let refreshing=null;

  const normalizeText=v=>String(v||'').toLowerCase().replace(/^\s*\d+[.)]\s*/,'').replace(/\s+/g,' ').trim();
  const safeUrl=value=>{
    try{
      const u=new URL(value,location.href);
      ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','fbclid'].forEach(k=>u.searchParams.delete(k));
      u.hash='';
      return u.href.replace(/\/$/,'');
    }catch{return String(value||'').trim();}
  };

  function activeTab(){
    const active=document.querySelector('.tab.active[data-category],.tab.active[data-tab],.tab.active');
    if(active){
      const value=active.dataset.category||active.dataset.tab||active.getAttribute('data-key')||active.textContent;
      if(value)return normalizeText(value);
    }
    return normalizeText(document.body.dataset.activeTab||window.active||'unknown');
  }

  function tabFor(card){
    const explicit=card.dataset.category||card.dataset.tab;
    if(explicit)return normalizeText(explicit);
    const section=card.closest('[data-category],[data-tab],section[id],div[id^="section-"]');
    if(section){
      const value=section.dataset.category||section.dataset.tab||String(section.id||'').replace(/^(section-|tab-)/i,'');
      if(value)return normalizeText(value);
    }
    return activeTab();
  }

  function snapshot(card){
    const titleLink=card.querySelector('h3 a[href],h2 a[href],.title a[href],a.story-link[href]');
    const fallbackLink=card.querySelector('a[href]');
    const link=titleLink||fallbackLink;
    const titleNode=card.querySelector('h3,h2,.title,.headline');
    const sourceNode=card.querySelector('.source,[data-source],.meta .source-name');
    const descNode=card.querySelector('.description,.summary,.dek');
    const whyNode=card.querySelector('.why,.v3-why-text');
    const title=(titleNode?.textContent||link?.textContent||'').trim();
    const url=safeUrl(link?.href||'');
    const source=(sourceNode?.textContent||sourceNode?.getAttribute('data-source')||'').trim();
    const description=(descNode?.textContent||'').trim();
    const why=(whyNode?.textContent||'').trim();
    const tab=tabFor(card);
    return {
      title,url,source,description,why,tab,
      titleKey:normalizeText(title),urlKey:url.toLowerCase(),sourceKey:normalizeText(source),
      capturedAt:new Date().toISOString()
    };
  }

  function sameRecord(record,data){
    const recordTab=normalizeText(record.category||record.tab);
    if(recordTab!==normalizeText(data.tab))return false;
    const recordUrl=String(record.url_key||record.urlKey||record.url||'').toLowerCase();
    const recordTitle=normalizeText(record.title_key||record.titleKey||record.title);
    const recordSource=normalizeText(record.source_key||record.sourceKey||record.source);
    if(recordUrl&&data.urlKey&&recordUrl===data.urlKey)return true;
    return !!recordTitle&&recordTitle===data.titleKey&&recordSource===data.sourceKey;
  }

  function suppressed(data){
    return REASONS.some(reason=>remotePools[reason].some(record=>sameRecord(record,data)));
  }

  async function refreshPools(){
    if(refreshing)return refreshing;
    refreshing=(async()=>{
      const response=await fetch(API_URL,{method:'GET',cache:'no-store',headers:{Accept:'application/json'}});
      if(!response.ok)throw new Error(`Feedback pool read failed (${response.status})`);
      const payload=await response.json();
      REASONS.forEach(reason=>{remotePools[reason]=Array.isArray(payload?.pools?.[reason])?payload.pools[reason]:[];});
      document.dispatchEvent(new CustomEvent('underreported:feedback-pools-refreshed',{detail:counts()}));
      return remotePools;
    })().finally(()=>{refreshing=null;});
    return refreshing;
  }

  function counts(){return {D:remotePools.D.length,NR:remotePools.NR.length,NW:remotePools.NW.length};}

  function syncVisibleCount(){
    const root=document.getElementById('news-feed');
    if(!root)return;
    const visible=root.querySelectorAll('.news-item:not(.feedback-removing)').length;
    const countEl=root.querySelector('.section .section-header .count');
    if(countEl&&/^Showing\s+\d+/i.test(countEl.textContent||'')){
      countEl.textContent=(countEl.textContent||'').replace(/^Showing\s+\d+/i,`Showing ${visible}`);
    }
  }

  function backfill(tab){
    const key=normalizeText(tab);
    if(!key||activeTab()!==key||key==='boxoffice')return;
    const countsObj=window.loadCounts;
    if(countsObj&&typeof countsObj==='object'){
      const current=Number(countsObj[key]||50);
      countsObj[key]=Number.isFinite(current)?current+1:51;
    }
    const renderFn=window.canonicalRender||window.render;
    const items=window.allItems||(typeof allItems!=='undefined'?allItems:null);
    if(typeof renderFn!=='function'||!items){
      document.dispatchEvent(new CustomEvent('underreported:feedback-backfill',{detail:{tab:key}}));
      return;
    }
    window.requestAnimationFrame(()=>{
      renderFn(items);
      window.requestAnimationFrame(()=>{
        decorate(document);
        syncVisibleCount();
      });
    });
  }

  function removeCard(card,tab){
    card.classList.add('feedback-removing');
    window.setTimeout(()=>{
      card.remove();
      backfill(tab);
    },150);
  }

  async function record(reason,card){
    const data=snapshot(card);
    if(!data.title&&!data.url)return;
    const controls=card.querySelector(':scope > .card-feedback-controls');
    controls?.querySelectorAll('button').forEach(button=>{button.disabled=true;});
    try{
      const response=await fetch(API_URL,{
        method:'POST',
        headers:{'Content-Type':'application/json',Accept:'application/json'},
        body:JSON.stringify({
          reason,
          category:data.tab,
          title:data.title,
          url:data.url,
          source:data.source,
          description:data.description,
          why:data.why,
          capturedAt:data.capturedAt
        })
      });
      if(!response.ok)throw new Error(`Feedback write failed (${response.status})`);
      const entry={
        reason,category:data.tab,title:data.title,url:data.url,source:data.source,
        title_key:data.titleKey,url_key:data.urlKey,source_key:data.sourceKey,captured_at:data.capturedAt
      };
      if(!remotePools[reason].some(existing=>sameRecord(existing,data)))remotePools[reason].push(entry);
      removeCard(card,data.tab);
      document.dispatchEvent(new CustomEvent('underreported:card-feedback',{detail:entry}));
    }catch(error){
      console.error('Could not save article feedback:',error);
      controls?.querySelectorAll('button').forEach(button=>{button.disabled=false;});
      if(controls){controls.dataset.error='1';controls.title='Feedback was not saved. Tap again to retry.';}
    }
  }

  function eligible(card){
    if(!(card instanceof Element))return false;
    if(card.matches('.nfl-game-card,.nfl-live-center,.bookmark-section .news-item[data-bookmark-clone="1"]'))return false;
    if(tabFor(card)==='boxoffice'||activeTab()==='boxoffice')return false;
    return !!card.querySelector('h3 a[href],h2 a[href],.title a[href],a.story-link[href],a[href]');
  }

  function decorateCard(card){
    if(!eligible(card)){
      card.querySelector(':scope > .card-feedback-controls')?.remove();
      card.classList.remove('has-card-feedback');
      return;
    }
    const data=snapshot(card);
    if(suppressed(data)){card.remove();return;}
    if(card.querySelector(':scope > .card-feedback-controls'))return;
    card.classList.add('has-card-feedback');
    const controls=document.createElement('div');
    controls.className='card-feedback-controls';
    controls.setAttribute('role','group');
    controls.setAttribute('aria-label','Article feedback');
    const labels={D:'Duplicate',NR:'Not Relevant',NW:'Not Wanted'};
    REASONS.forEach(reason=>{
      const button=document.createElement('button');
      button.type='button';
      button.className='card-feedback-btn';
      button.dataset.feedback=reason;
      button.textContent=reason;
      button.title=labels[reason];
      button.setAttribute('aria-label',labels[reason]);
      button.addEventListener('click',event=>{
        event.preventDefault();event.stopPropagation();record(reason,card);
      });
      controls.appendChild(button);
    });
    card.appendChild(controls);
  }

  function decorate(root=document){
    if(decorating)return;
    decorating=true;
    try{
      if(root instanceof Element&&root.matches('.news-item'))decorateCard(root);
      root.querySelectorAll?.('.news-item').forEach(card=>decorateCard(card));
    }finally{decorating=false;}
  }

  async function start(){
    try{await refreshPools();}catch(error){console.error('Could not load persistent feedback pools:',error);}
    decorate(document);
    const observer=new MutationObserver(mutations=>{
      mutations.forEach(mutation=>mutation.addedNodes.forEach(node=>{
        if(!(node instanceof Element))return;
        if(node.matches('.news-item'))decorateCard(node);
        node.querySelectorAll?.('.news-item').forEach(card=>decorateCard(card));
      }));
    });
    observer.observe(document.body,{childList:true,subtree:true});

    window.UnderreportedFeedback={
      getPools:()=>JSON.parse(JSON.stringify(remotePools)),
      counts,
      toJSON:()=>JSON.stringify(remotePools,null,2),
      refresh:async()=>{await refreshPools();decorate(document);return counts();},
      backfill
    };
    document.documentElement.dataset.cardFeedback='persistent';
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
