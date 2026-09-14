(()=>{
  'use strict';
  const STORAGE_KEY='underreported.cardFeedback.v1';
  const REASONS=['D','NR','NW'];
  let decorating=false;

  const normalizeText=v=>String(v||'').toLowerCase().replace(/^\s*\d+[.)]\s*/,'').replace(/\s+/g,' ').trim();
  const safeUrl=value=>{
    try{
      const u=new URL(value,location.href);
      ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','fbclid'].forEach(k=>u.searchParams.delete(k));
      u.hash='';
      return u.href.replace(/\/$/,'');
    }catch{return String(value||'').trim();}
  };
  const load=()=>{
    try{
      const raw=JSON.parse(localStorage.getItem(STORAGE_KEY)||'{}');
      const pools={D:[],NR:[],NW:[]};
      REASONS.forEach(r=>{if(Array.isArray(raw[r])) pools[r]=raw[r];});
      return pools;
    }catch{return {D:[],NR:[],NW:[]};}
  };
  const save=pools=>localStorage.setItem(STORAGE_KEY,JSON.stringify(pools));

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
    if(normalizeText(record.tab)!==normalizeText(data.tab))return false;
    if(record.urlKey&&data.urlKey&&record.urlKey===data.urlKey)return true;
    return !!record.titleKey&&record.titleKey===data.titleKey&&normalizeText(record.sourceKey||record.source)===data.sourceKey;
  }

  function suppressed(data,pools){
    return REASONS.some(reason=>pools[reason].some(record=>sameRecord(record,data)));
  }

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
    if(!key||activeTab()!==key)return;
    const counts=window.loadCounts;
    if(counts&&typeof counts==='object'){
      const current=Number(counts[key]||10);
      counts[key]=Number.isFinite(current)?current+1:11;
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

  function record(reason,card){
    const data=snapshot(card);
    if(!data.title&&!data.url)return;
    const pools=load();
    const entry={...data,reason};
    if(!pools[reason].some(existing=>sameRecord(existing,data)))pools[reason].push(entry);
    save(pools);
    removeCard(card,data.tab);
    document.dispatchEvent(new CustomEvent('underreported:card-feedback',{detail:entry}));
  }

  function eligible(card){
    if(!(card instanceof Element))return false;
    if(card.matches('.nfl-game-card,.nfl-live-center,.bookmark-section .news-item[data-bookmark-clone="1"]'))return false;
    return !!card.querySelector('h3 a[href],h2 a[href],.title a[href],a.story-link[href],a[href]');
  }

  function decorateCard(card,pools){
    if(!eligible(card))return;
    const data=snapshot(card);
    if(suppressed(data,pools)){card.remove();return;}
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
      const pools=load();
      if(root instanceof Element&&root.matches('.news-item'))decorateCard(root,pools);
      root.querySelectorAll?.('.news-item').forEach(card=>decorateCard(card,pools));
    }finally{decorating=false;}
  }

  function start(){
    decorate(document);
    const observer=new MutationObserver(mutations=>{
      const pools=load();
      mutations.forEach(mutation=>mutation.addedNodes.forEach(node=>{
        if(!(node instanceof Element))return;
        if(node.matches('.news-item'))decorateCard(node,pools);
        node.querySelectorAll?.('.news-item').forEach(card=>decorateCard(card,pools));
      }));
    });
    observer.observe(document.body,{childList:true,subtree:true});

    window.UnderreportedFeedback={
      getPools:()=>JSON.parse(JSON.stringify(load())),
      counts:()=>{const p=load();return {D:p.D.length,NR:p.NR.length,NW:p.NW.length};},
      toJSON:()=>JSON.stringify(load(),null,2),
      clear:()=>{localStorage.removeItem(STORAGE_KEY);decorate(document);},
      backfill
    };
    document.documentElement.dataset.cardFeedback='ready';
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
