/* Underreported 3.1 — non-destructive presentation enhancements. */
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
  const railClasses=['rail-blue','rail-green','rail-orange','rail-purple','rail-red'];
  const legendExcluded=new Set(['nfl','boxoffice']);

  function cleanWhy(text){
    return String(text||'').replace(/^\s*why\s+it\s+matters\s*[:—-]?\s*/i,'').trim();
  }

  function currentSection(){
    try{
      if(typeof active!=='undefined'&&active)return String(active);
    }catch(e){}
    return document.body?.dataset?.activeTab||'';
  }

  function bookmarksVisible(){
    return !!document.getElementById('bookmarks-tab')?.classList.contains('active')||!!document.querySelector('#news-feed .bookmark-section');
  }

  function removeRetiredHierarchyLegend(root=document){
    root.querySelectorAll?.('.v3-card-key').forEach(el=>el.remove());
  }

  function installAgeStyles(){
    if(document.getElementById('underreported-age-styles-v31'))return;
    const style=document.createElement('style');
    style.id='underreported-age-styles-v31';
    style.textContent=`
      .news-item.underreported-item.age-blue{border-left:5px solid #2563eb!important}
      .news-item.underreported-item.age-green{border-left:5px solid #16a34a!important}
      .news-item.underreported-item.age-orange{border-left:5px solid #f97316!important}
      .news-item.underreported-item.age-purple{border-left:5px solid #9333ea!important}
      .news-item.underreported-item.age-red{border-left:5px solid #dc2626!important}
      .underreported-age-key,.feedback-legend{display:flex;flex-wrap:wrap;align-items:center;gap:7px 12px;margin:6px 0 14px;font-size:11px;line-height:1.35;color:var(--ui-muted,#64748b);opacity:.9}
      .underreported-age-key span,.feedback-legend span{display:inline-flex;align-items:center;gap:5px}
      .underreported-age-key i{display:inline-block;width:9px;height:9px;border-radius:2px;flex:0 0 auto}
      .underreported-age-key .b{background:#2563eb}.underreported-age-key .g{background:#16a34a}.underreported-age-key .o{background:#f97316}.underreported-age-key .p{background:#9333ea}.underreported-age-key .r{background:#dc2626}
      .underreported-age-key .feedback-code,.feedback-legend .feedback-code{display:inline-grid;place-items:center;min-width:22px;height:18px;padding:0 5px;border:1px solid var(--ui-line,#dbe2ea);border-radius:999px;background:rgba(127,127,127,.07);color:var(--ui-text,#334155);font-size:9px;font-weight:900;line-height:1}
      .underreported-age-key .feedback-divider{width:1px;height:16px;background:var(--ui-line,#dbe2ea);margin:0 1px}
      @media(max-width:600px){.underreported-age-key,.feedback-legend{font-size:10px;gap:6px 9px;margin:6px 0 12px}.underreported-age-key .feedback-divider{display:none}}
    `;
    document.head.appendChild(style);
  }

  function decorateUnderreportedAge(card){
    if(!card.classList.contains('underreported-item'))return;
    card.classList.remove('age-blue','age-green','age-orange','age-purple','age-red');
    const valid=new Set(['blue','green','orange','purple','red']);
    const feedBand=String(card.dataset.ageBand||'').trim().toLowerCase();
    if(valid.has(feedBand)){
      card.classList.add('age-'+feedBand);
      return;
    }
    const raw=card.dataset.pubDate||card.querySelector('.meta span:first-child')?.textContent?.trim()||'';
    const dt=new Date(raw);
    if(Number.isNaN(dt.getTime()))return;
    const age=Math.max(0,(Date.now()-dt.getTime())/86400000);
    let cls='age-red';
    if(age<=2)cls='age-blue';
    else if(age<=4)cls='age-green';
    else if(age<=7)cls='age-orange';
    else if(age<=10)cls='age-purple';
    card.classList.add(cls);
  }

  function decorateImportanceRail(card){
    if(card.classList.contains('underreported-item')||card.classList.contains('nfl-game-card'))return;
    railClasses.forEach(cls=>card.classList.remove(cls));
    const title=card.querySelector('h3,h2,.title,.headline')?.textContent||'';
    const desc=card.querySelector('.description,.summary,.dek')?.textContent||'';
    const text=` ${title} ${desc} `.toLowerCase();
    let cls='rail-blue';
    if(/\b(breaking|deadly|killed|mass shooting|earthquake|hurricane|wildfire|evacuat(?:e|ion)|airstrike|missile strike|invasion|ceasefire|state of emergency|major outage|data breach|cyberattack)\b/.test(text)){
      cls='rail-red';
    }else if(/\b(developing|investigation|indict(?:ed|ment)|arrest(?:ed)?|lawsuit|court rules?|strike|shutdown|recall|outbreak|tariffs?|layoffs?|bankruptcy|fraud|charges?)\b/.test(text)){
      cls='rail-orange';
    }else if(/\b(congress|senate|house of representatives|white house|president|federal|supreme court|legislation|\bbill\b|executive order|election|voters?|governor|policy|regulation|rulemaking)\b/.test(text)){
      cls='rail-purple';
    }else if(/\b(science|research|study finds?|breakthrough|discovery|health|medical|renewable|education|achievement|award|solution|conservation|recovery)\b/.test(text)){
      cls='rail-green';
    }
    card.classList.add(cls);
    card.dataset.railHierarchy=cls.replace('rail-','');
  }

  function feedbackLegendMarkup(){
    return '<span><b class="feedback-code">D</b>Duplicate</span><span><b class="feedback-code">NR</b>Not Relevant</span><span><b class="feedback-code">NW</b>Not Wanted</span>';
  }

  function installLegend(){
    document.querySelectorAll('#news-feed .underreported-age-key,#news-feed .feedback-legend').forEach(el=>el.remove());
    const section=document.querySelector('#news-feed .section');
    if(!section||bookmarksVisible())return;
    const current=currentSection();
    if(!current||legendExcluded.has(current))return;
    const key=document.createElement('div');
    if(current==='underreported'){
      key.className='underreported-age-key';
      key.setAttribute('aria-label','Underreported story age colors and feedback controls');
      key.innerHTML='<span><i class="b"></i>0–2 days</span><span><i class="g"></i>2–4 days</span><span><i class="o"></i>4–7 days</span><span><i class="p"></i>7–10 days</span><span><i class="r"></i>10–14 days</span><span class="feedback-divider" aria-hidden="true"></span>'+feedbackLegendMarkup();
    }else{
      key.className='feedback-legend';
      key.setAttribute('aria-label','Article feedback controls');
      key.innerHTML=feedbackLegendMarkup();
    }
    const head=section.querySelector('.section-header');
    if(head)head.after(key);
    else section.prepend(key);
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
    removeRetiredHierarchyLegend(root);
    root.querySelectorAll?.('.news-item').forEach(card=>{
      decorateWhy(card);
      decorateSource(card);
      decorateUnderreportedAge(card);
      decorateImportanceRail(card);
    });
    installLegend();
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

  function compactCountdown(){
    const target=Number(window.nextScheduledPull)||0;
    if(!target)return '';
    const total=Math.max(0,Math.ceil((target-Date.now())/1000));
    const h=Math.floor(total/3600);
    const m=Math.floor((total%3600)/60);
    const s=total%60;
    if(h)return `${h}h ${String(m).padStart(2,'0')}m`;
    return `${m}m ${String(s).padStart(2,'0')}s`;
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
      const countdown=compactCountdown()||countdownMatch?.[1]?.trim()||'';
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

    if(window.__v3UtilityStatusTimer)clearInterval(window.__v3UtilityStatusTimer);
    window.__v3UtilityStatusTimer=setInterval(sync,1000);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();},{passive:true});
  }

  function refresh(){
    if(document.body)document.body.dataset.underreportedVersion='3.1';
    removeRetiredHierarchyLegend();
    installAgeStyles();
    installUtilityStatus();
    processTabs();
    processCards();
  }

  function start(){
    refresh();
    const feed=document.getElementById('news-feed');
    const tabs=document.getElementById('tabs');
    if(feed)new MutationObserver(()=>processCards(feed)).observe(feed,{childList:true});
    if(tabs)new MutationObserver(processTabs).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    document.addEventListener('click',e=>{
      if(e.target.closest('.tab'))requestAnimationFrame(()=>{processTabs();processCards();});
    });
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();