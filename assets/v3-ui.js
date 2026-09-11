/* Underreported 3.0 — non-destructive presentation enhancements. */
(function(){
  'use strict';

  const sourceMarks=[
    [/\breuters\b/i,'R'],
    [/associated press|\bap\b/i,'AP'],
    [/\bcbs\b/i,'CBS'],
    [/colorado sun/i,'CS'],
    [/\bnpr\b/i,'NPR'],
    [/denver post/i,'DP']
  ];

  function cleanWhy(text){
    return String(text||'').replace(/^\s*why\s+it\s+matters\s*[:—-]?\s*/i,'').trim();
  }

  function currentSection(){
    try{
      if(typeof active!=='undefined'&&active)return String(active);
    }catch(e){}
    return document.body?.dataset?.activeTab||'';
  }

  function addImportance(card){
    if(card.querySelector('.v3-importance'))return;
    let label='',kind='';
    const section=currentSection();
    if(card.classList.contains('lead-story-v2')){label='HIGH IMPACT';kind='high';}
    else if(card.classList.contains('underreported-item')||section==='underreported'){label='ANALYSIS';kind='analysis';}
    else if(section==='local'){label='LOCAL';kind='local';}
    else if(card.classList.contains('x-issue-item')||section==='x'){label='TRENDING';kind='trending';}
    if(!label)return;
    const badge=document.createElement('span');
    badge.className='v3-importance '+kind;
    badge.textContent=label;
    card.prepend(badge);
  }

  function decorateWhy(card){
    const why=card.querySelector('.why');
    if(!why||why.dataset.v3==='1')return;
    const text=cleanWhy(why.textContent);
    if(!text)return;
    why.textContent='';
    const label=document.createElement('strong');
    label.className='v3-why-label';
    label.textContent='WHY IT MATTERS';
    const body=document.createElement('span');
    body.className='v3-why-text';
    body.textContent=text;
    why.append(label,body);
    why.dataset.v3='1';

    const titleBlock=card.querySelector('.bookmark-row')||card.querySelector('h3');
    if(titleBlock&&titleBlock.nextElementSibling!==why)titleBlock.after(why);
  }

  function decorateSource(card){
    const source=card.querySelector('.source');
    if(!source||source.querySelector('.v3-source-icon'))return;
    const original=source.textContent.trim();
    const hit=sourceMarks.find(([pattern])=>pattern.test(original));
    if(!hit)return;
    const icon=document.createElement('span');
    icon.className='v3-source-icon';
    icon.setAttribute('aria-hidden','true');
    icon.textContent=hit[1];
    source.prepend(icon);
  }

  function processCards(root=document){
    root.querySelectorAll?.('.news-item').forEach(card=>{
      decorateWhy(card);
      decorateSource(card);
      addImportance(card);
    });
  }

  function processTabs(){
    document.querySelectorAll('.tab').forEach(tab=>{
      if(tab.classList.contains('active'))tab.setAttribute('aria-current','page');
      else tab.removeAttribute('aria-current');
    });
  }

  function compactStateLabel(value){
    const text=String(value||'').replace(/^\s*[✓↻⚠]\s*/,'').trim();
    if(/auto refresh active/i.test(text))return 'Auto update';
    if(/auto refresh checking/i.test(text))return 'Checking';
    if(/auto refresh retrying/i.test(text))return 'Retrying';
    if(/feed update delayed/i.test(text))return 'Update delayed';
    return text||'Auto update';
  }

  function installUtilityStatus(){
    const toolbar=document.querySelector('.toolbar');
    const pull=document.getElementById('pull-stats-ui');
    const local=document.getElementById('local-status');
    if(!toolbar||!pull||document.getElementById('v3-auto-status'))return;
    const compact=document.createElement('span');
    compact.id='v3-auto-status';
    compact.setAttribute('aria-label','Automatic refresh status');

    function sync(){
      const state=compactStateLabel(pull.querySelector('.status-state')?.textContent?.trim()||'Auto update');
      const lines=[...pull.querySelectorAll('.status-line')].map(line=>line.textContent.replace(/\s+/g,' ').trim());
      const allText=pull.textContent.replace(/\s+/g,' ').trim();
      const countdownMatch=(lines[0]||allText).match(/Next in\s+([^•]+)/i);
      const fetchedMatch=allText.match(/(\d+)\s+fetched/i);
      const countdown=countdownMatch?.[1]?.trim()||'';
      const fetched=fetchedMatch?.[1]||'';
      const parts=[state];
      if(fetched)parts.push(fetched+' fetched');
      if(countdown)parts.push(countdown);
      compact.textContent=parts.join(' · ');
      compact.dataset.countdown=countdown;
      compact.dataset.fetched=fetched;
      compact.title=allText;
    }

    function applyMobileLayout(){
      const mobile=window.matchMedia('(max-width:760px)').matches;
      const status=document.getElementById('status');
      if(mobile){
        compact.style.setProperty('display','inline-flex','important');
        compact.style.setProperty('flex','1 1 145px','important');
        compact.style.setProperty('max-width','200px','important');
        compact.style.setProperty('font-size','8.5px','important');
        if(status)status.style.setProperty('display','none','important');
      }else{
        compact.style.removeProperty('display');
        compact.style.removeProperty('flex');
        compact.style.removeProperty('max-width');
        compact.style.removeProperty('font-size');
        if(status)status.style.removeProperty('display');
      }
    }

    sync();
    applyMobileLayout();
    if(local)toolbar.insertBefore(compact,local);else toolbar.appendChild(compact);
    new MutationObserver(sync).observe(pull,{subtree:true,childList:true,characterData:true,attributes:true});
    window.addEventListener('resize',applyMobileLayout,{passive:true});
  }

  function refresh(){
    if(document.body)document.body.dataset.underreportedVersion='3';
    installUtilityStatus();
    processTabs();
    processCards();
  }

  function start(){
    refresh();
    const feed=document.getElementById('news-feed');
    const tabs=document.getElementById('tabs');
    if(feed)new MutationObserver(()=>processCards(feed)).observe(feed,{childList:true,subtree:true});
    if(tabs)new MutationObserver(processTabs).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    document.addEventListener('click',e=>{
      if(e.target.closest('.tab'))requestAnimationFrame(()=>{processTabs();processCards();});
    });
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();