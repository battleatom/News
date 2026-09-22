(()=>{
  'use strict';
  const API_URL='/api/feedback';
  const REASONS=['D','NR','NW'];
  const FALLBACK_DESTINATIONS=[
    ['top','Top Stories'],['nfl','NFL'],['christian','Christian'],['x','X'],['underreported','Underreported'],['world','World'],['us','United States'],['presidential','Presidential'],
    ['federal','Federal Government'],['legislation','Laws & Legislation'],['nm','New Mexico'],['local','Local'],['region','Region'],
    ['technology','Technology'],['gaming','Gaming & Computing'],['military','Military & War'],['entertainment','Entertainment']
  ];
  function destinations(){
    const live=[...document.querySelectorAll('#tabs .tab[data-category]')].map(tab=>[tab.dataset.category,tab.querySelector('span:not([aria-hidden])')?.textContent?.trim()||tab.textContent.replace(/\d+\s*(?:\/\s*\d+)?\s*$/,'').trim()]).filter(([key])=>key&&!['admin','bookmarks','boxoffice'].includes(key));
    const seen=new Set(live.map(([key])=>key));return [...live,...FALLBACK_DESTINATIONS.filter(([key])=>!seen.has(key))];
  }
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
    const publishedNode=card.querySelector('time,[datetime],.pubdate,.published,.date');
    const imageNode=card.querySelector('img[src]');
    const title=(titleNode?.textContent||link?.textContent||'').trim();
    const url=safeUrl(link?.href||'');
    const source=(sourceNode?.textContent||sourceNode?.getAttribute('data-source')||'').trim();
    const description=(descNode?.textContent||'').trim();
    const why=(whyNode?.textContent||'').trim();
    const tab=tabFor(card);
    const publishedAt=(publishedNode?.getAttribute('datetime')||publishedNode?.textContent||'').trim();
    const imageUrl=safeUrl(imageNode?.currentSrc||imageNode?.src||'');
    const storyId=String(card.dataset.storyId||card.dataset.id||'').trim();
    return {
      title,url,source,description,why,tab,publishedAt,imageUrl,storyId,
      titleKey:normalizeText(title),urlKey:url.toLowerCase(),sourceKey:normalizeText(source),
      capturedAt:new Date().toISOString()
    };
  }

  function sameRecord(record,data,requireCategory=true){
    const recordTab=normalizeText(record.category||record.tab);
    if(requireCategory&&recordTab&&recordTab!==normalizeText(data.tab))return false;
    const recordUrl=String(record.url_key||record.urlKey||record.url||'').toLowerCase();
    const recordTitle=normalizeText(record.title_key||record.titleKey||record.title);
    const recordSource=normalizeText(record.source_key||record.sourceKey||record.source);
    if(recordUrl&&data.urlKey&&recordUrl===data.urlKey)return true;
    return !!recordTitle&&recordTitle===data.titleKey&&recordSource===data.sourceKey;
  }

  function suppressed(data){
    if(remotePools.D.some(record=>sameRecord(record,data,false)))return true;
    return ['NR','NW'].some(reason=>remotePools[reason].some(record=>sameRecord(record,data,true)));
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

  function chooseDestination(card){
    const current=tabFor(card);
    return new Promise(resolve=>{
      document.querySelector('.nr-destination-picker')?.remove();
      const overlay=document.createElement('div');
      overlay.className='nr-destination-picker';
      Object.assign(overlay.style,{position:'fixed',inset:'0',zIndex:'2147483647',background:'rgba(0,0,0,.52)',display:'flex',alignItems:'center',justifyContent:'center',padding:'18px'});
      const panel=document.createElement('div');
      Object.assign(panel.style,{width:'min(440px,100%)',maxHeight:'80vh',overflow:'auto',background:'var(--card-bg,#fff)',color:'var(--text-color,#111)',borderRadius:'16px',padding:'18px',boxShadow:'0 18px 60px rgba(0,0,0,.35)'});
      const heading=document.createElement('div'); heading.textContent='Where should this story go?'; Object.assign(heading.style,{fontWeight:'800',fontSize:'18px',marginBottom:'12px'}); panel.appendChild(heading);
      const grid=document.createElement('div'); Object.assign(grid.style,{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:'8px'});
      destinations().filter(([key])=>key!==current).forEach(([key,label])=>{
        const b=document.createElement('button'); b.type='button'; b.textContent=label;
        Object.assign(b.style,{padding:'11px 10px',borderRadius:'10px',border:'1px solid rgba(127,127,127,.35)',background:'transparent',color:'inherit',fontWeight:'700',cursor:'pointer'});
        b.onclick=e=>{e.preventDefault();e.stopPropagation();overlay.remove();resolve(key);}; grid.appendChild(b);
      });
      panel.appendChild(grid);
      const cancel=document.createElement('button'); cancel.type='button'; cancel.textContent='Cancel';
      Object.assign(cancel.style,{marginTop:'12px',width:'100%',padding:'10px',border:'0',background:'transparent',color:'inherit',cursor:'pointer'});
      cancel.onclick=e=>{e.preventDefault();e.stopPropagation();overlay.remove();resolve(null);}; panel.appendChild(cancel);
      overlay.onclick=e=>{if(e.target===overlay){overlay.remove();resolve(null);}};
      overlay.appendChild(panel); document.body.appendChild(overlay);
    });
  }

  async function record(reason,card,targetCategory=''){
    const data=snapshot(card);
    if(!data.title&&!data.url)return;
    const controls=card.querySelector(':scope > .card-feedback-controls');
    controls?.querySelectorAll('button').forEach(button=>{button.disabled=true;});
    try{
      const response=await fetch(API_URL,{
        method:'POST',
        headers:{'Content-Type':'application/json',Accept:'application/json',...(window.DPoolSecurity?.headers?.()||{})},
        body:JSON.stringify({
          reason,
          category:data.tab,
          title:data.title,
          url:data.url,
          source:data.source,
          description:data.description,
          why:data.why,
          publishedAt:data.publishedAt,
          imageUrl:data.imageUrl,
          storyId:data.storyId,
          originalCategory:data.tab,
          targetCategory:targetCategory||null,
          schemaVersion:2,
          capturedAt:data.capturedAt
        })
      });
      if(!response.ok){let detail='';try{detail=(await response.json())?.error||''}catch{};if(response.status===401)sessionStorage.removeItem('dpoolAdminSession');throw new Error(detail||`Feedback write failed (${response.status})`);}
      const entry={
        reason,category:data.tab,title:data.title,url:data.url,source:data.source,
        description:data.description,why:data.why,published_at:data.publishedAt,image_url:data.imageUrl,story_id:data.storyId,original_category:data.tab,target_category:targetCategory||null,schema_version:2,title_key:data.titleKey,url_key:data.urlKey,source_key:data.sourceKey,captured_at:data.capturedAt
      };
      const globalReason=reason==='D';
      if(!remotePools[reason].some(existing=>sameRecord(existing,data,!globalReason)))remotePools[reason].push(entry);
      removeCard(card,data.tab);
      document.dispatchEvent(new CustomEvent('underreported:card-feedback',{detail:entry}));
    }catch(error){
      console.error('Could not save article feedback:',error);
      controls?.querySelectorAll('button').forEach(button=>{button.disabled=false;});
      if(controls){controls.dataset.error='1';controls.title='Feedback was not saved. Tap again to retry.';} const t=document.getElementById('toast');if(t){t.textContent=error?.message||'Feedback was not saved';t.hidden=false;clearTimeout(record.toastTimer);record.toastTimer=setTimeout(()=>{t.hidden=true},3000)}
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
    const labels={D:'Duplicate',NR:'Wrong Section',NW:'Vague / Weak Title'};
    REASONS.forEach(reason=>{
      const button=document.createElement('button');
      button.type='button';
      button.className='card-feedback-btn';
      button.dataset.feedback=reason;
      button.textContent=reason;
      button.title=labels[reason];
      button.setAttribute('aria-label',labels[reason]);
      button.addEventListener('click',async event=>{
        event.preventDefault();event.stopPropagation();
        const auth=await window.DPoolSecurity?.requireAuth?.();if(!auth)return;
        if(reason==='NR'){
          const target=await chooseDestination(card);
          if(!target)return;
          await record(reason,card,target);
        }else await record(reason,card);
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
