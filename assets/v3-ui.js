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

  function cleanWhy(text){
    return String(text||'').replace(/^\s*why\s+it\s+matters\s*[:—-]?\s*/i,'').trim();
  }

  function currentSection(){
    try{
      if(typeof active!=='undefined'&&active)return String(active);
    }catch(e){}
    return document.body?.dataset?.activeTab||'';
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
      .underreported-age-key{display:flex;flex-wrap:wrap;gap:8px 12px;margin:6px 0 12px;font-size:11px;opacity:.82}
      .underreported-age-key span{display:inline-flex;align-items:center;gap:5px}
      .underreported-age-key i{display:inline-block;width:9px;height:9px;border-radius:2px}
      .underreported-age-key .b{background:#2563eb}.underreported-age-key .g{background:#16a34a}.underreported-age-key .o{background:#f97316}.underreported-age-key .p{background:#9333ea}.underreported-age-key .r{background:#dc2626}
    `;
    document.head.appendChild(style);
  }

  function decorateUnderreportedAge(card){
    if(!card.classList.contains('underreported-item'))return;
    card.classList.remove('age-blue','age-green','age-orange','age-purple','age-red');
    const raw=card.querySelector('.meta span:first-child')?.textContent?.trim()||'';
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

  function installUnderreportedLegend(){
    if(currentSection()!=='underreported')return;
    const section=document.querySelector('#news-feed .section');
    if(!section||section.querySelector('.underreported-age-key'))return;
    const key=document.createElement('div');
    key.className='underreported-age-key';
    key.innerHTML='<span><i class="b"></i>0–2 days</span><span><i class="g"></i>2–4 days</span><span><i class="o"></i>4–7 days</span><span><i class="p"></i>7–10 days</span><span><i class="r"></i>10–14 days</span>';
    const body=section.querySelector('.section-body');
    if(body)section.insertBefore(key,body);
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
      decorateUnderreportedAge(card);
    });
    installUnderreportedLegend();
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

    // Keep the compact countdown independent from pull-status DOM mutations.
    // A short interval makes the displayed seconds resilient to timer drift,
    // throttling and mobile layout timing while remaining extremely cheap.
    if(window.__v3UtilityStatusTimer)clearInterval(window.__v3UtilityStatusTimer);
    window.__v3UtilityStatusTimer=setInterval(sync,250);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();},{passive:true});
  }

  function refresh(){
    if(document.body)document.body.dataset.underreportedVersion='3.1';
    installAgeStyles();
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