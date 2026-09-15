(()=>{
  'use strict';

  const RAIL_COLORS={
    blue:'#2563eb',
    green:'#16a34a',
    orange:'#f97316',
    purple:'#9333ea',
    red:'#dc2626'
  };
  const RAIL_CLASSES=['rail-blue','rail-green','rail-orange','rail-purple','rail-red'];
  const BOXOFFICE_RAIL_COLORS={cyan:'#06b6d4',blue:'#2563eb',green:'#16a34a',red:'#dc2626'};

  function canonicalTabKey(value){
    let text=String(value||'').toLowerCase().trim();
    text=text.replace(/[^a-z0-9&]+/g,' ').replace(/\s+/g,' ').trim();
    const compact=text.replace(/[^a-z0-9]+/g,'');
    const aliases={
      boxoffice:'boxoffice',
      boxofficemovies:'boxoffice',
      topstories:'top',
      topissues:'x',
      unitedstates:'us',
      federalgovernment:'federal',
      lawslegislation:'legislation',
      newmexico:'nm',
      gamingcomputing:'gaming',
      militarywar:'military'
    };
    return aliases[compact]||compact||'unknown';
  }

  function activeTabKey(){
    try{
      if(typeof active!=='undefined'&&active)return canonicalTabKey(active);
    }catch(e){}
    if(window.active)return canonicalTabKey(window.active);
    const selected=document.querySelector('.tab.active');
    if(selected){
      const raw=selected.dataset.category||selected.dataset.tab||selected.dataset.key||selected.textContent;
      if(raw)return canonicalTabKey(raw);
    }
    return canonicalTabKey(document.body?.dataset?.activeTab||'');
  }

  function clearBoxOfficeFeedback(root=document){
    if(activeTabKey()!=='boxoffice')return;
    root.querySelectorAll?.('.card-feedback-controls').forEach(el=>el.remove());
    root.querySelectorAll?.('.news-item.has-card-feedback').forEach(card=>card.classList.remove('has-card-feedback'));
  }

  function ensureBoxOfficeHotfixStyle(){
    if(document.getElementById('boxoffice-ux-hotfix-style'))return;
    const style=document.createElement('style');
    style.id='boxoffice-ux-hotfix-style';
    style.textContent=`
      .movie-news{margin-top:10px;font-size:.82rem;line-height:1.38}
      .movie-news .underreported-label{font-size:.72rem!important;letter-spacing:.08em}
      .movie-news a{display:block;margin-top:6px;font-size:.82rem!important;line-height:1.38!important;font-weight:600!important;text-decoration-thickness:1px}
      html body .boxoffice-section-title.boxoffice-coming-soon{border-left-color:#06b6d4!important}
      html body .news-item.movie-card.boxoffice-upcoming-card{border-left:5px solid #06b6d4!important}
      html body .news-item.movie-card.boxoffice-new-card{border-left:5px solid #2563eb!important}
      html body .news-item.movie-card.boxoffice-playing-card{border-left:5px solid #16a34a!important}
      html body .news-item.movie-card.boxoffice-leaving-card{border-left:5px solid #dc2626!important}
      @media(max-width:700px){.movie-news a{font-size:.8rem!important;line-height:1.36!important}}
    `;
    document.head.appendChild(style);
  }

  function boxOfficeCardDate(card){
    if(!(card instanceof Element))return 0;
    const pill=[...card.querySelectorAll('.movie-pill')].map(el=>(el.textContent||'').trim()).find(text=>/^Release(?:d)?\s+/i.test(text));
    if(!pill)return 0;
    const raw=pill.replace(/^Release(?:d)?\s*:?[ ]*/i,'').trim();
    const ts=Date.parse(raw);
    return Number.isFinite(ts)?ts:0;
  }

  function paintBoxOfficeCard(card,color,statusText){
    if(!(card instanceof Element)||!BOXOFFICE_RAIL_COLORS[color])return;
    ['boxoffice-upcoming-card','boxoffice-new-card','boxoffice-playing-card','boxoffice-leaving-card'].forEach(cls=>card.classList.remove(cls));
    const cls=color==='cyan'?'boxoffice-upcoming-card':color==='blue'?'boxoffice-new-card':color==='green'?'boxoffice-playing-card':'boxoffice-leaving-card';
    card.classList.add(cls);
    card.dataset.boxofficeRail=color;
    card.style.setProperty('border-left',`5px solid ${BOXOFFICE_RAIL_COLORS[color]}`,'important');
    card.style.setProperty('border-inline-start',`5px solid ${BOXOFFICE_RAIL_COLORS[color]}`,'important');
    const status=card.querySelector('.movie-status');
    if(status&&statusText)status.textContent=statusText;
  }

  function groupCards(heading){
    const cards=[];
    if(!(heading instanceof Element))return cards;
    let node=heading.nextElementSibling;
    while(node&&!node.classList.contains('boxoffice-section-title')){
      if(node.classList.contains('movie-card'))cards.push(node);
      node=node.nextElementSibling;
    }
    return cards;
  }

  function sortGroup(body,heading,cards,direction){
    if(!cards.length)return;
    const boundary=cards[cards.length-1].nextElementSibling;
    const sorted=[...cards].sort((a,b)=>direction*(boxOfficeCardDate(a)-boxOfficeCardDate(b))||((a.querySelector('h3')?.textContent||'').localeCompare(b.querySelector('h3')?.textContent||'')));
    const frag=document.createDocumentFragment();
    sorted.forEach(card=>frag.appendChild(card));
    body.insertBefore(frag,boundary);
  }

  function fixBoxOffice(root=document){
    if(activeTabKey()!=='boxoffice')return;
    ensureBoxOfficeHotfixStyle();
    const body=root.querySelector?.('#news-feed .section-body')||document.querySelector('#news-feed .section-body');
    if(!body)return;
    const headings=[...body.querySelectorAll(':scope > .boxoffice-section-title')];
    const upcomingHeading=headings.find(el=>/upcoming releases|coming soon/i.test(el.textContent||''));
    const currentHeading=headings.find(el=>/new\s*&\s*still in theaters|now playing/i.test(el.textContent||''));

    if(currentHeading){
      if(currentHeading.textContent!=='🎥 Now Playing — newest releases first')currentHeading.textContent='🎥 Now Playing — newest releases first';
      sortGroup(body,currentHeading,groupCards(currentHeading),-1);
      groupCards(currentHeading).forEach(card=>{
        const statusText=(card.querySelector('.movie-status')?.textContent||'').toLowerCase();
        if(statusText.includes('leaving')){paintBoxOfficeCard(card,'red','LEAVING SOON');return;}
        const released=boxOfficeCardDate(card);
        const ageDays=released?Math.floor((Date.now()-released)/86400000):999;
        if(ageDays>=0&&ageDays<=14)paintBoxOfficeCard(card,'blue','NEW RELEASE');
        else paintBoxOfficeCard(card,'green','NOW PLAYING');
      });
    }

    if(upcomingHeading){
      if(upcomingHeading.textContent!=='🩵 Coming Soon — next releases first')upcomingHeading.textContent='🩵 Coming Soon — next releases first';
      upcomingHeading.classList.add('boxoffice-coming-soon');
      const upcomingCards=groupCards(upcomingHeading);
      sortGroup(body,upcomingHeading,upcomingCards,1);
      const orderedUpcoming=groupCards(upcomingHeading);
      orderedUpcoming.forEach(card=>paintBoxOfficeCard(card,'cyan','COMING SOON'));
      if(currentHeading&&currentHeading.compareDocumentPosition(upcomingHeading)&Node.DOCUMENT_POSITION_FOLLOWING){
        const frag=document.createDocumentFragment();
        frag.appendChild(upcomingHeading);
        orderedUpcoming.forEach(card=>frag.appendChild(card));
        body.insertBefore(frag,currentHeading);
      }
    }
  }

  function importanceBand(card){
    const title=card.querySelector('h3,h2,.title,.headline')?.textContent||'';
    const desc=card.querySelector('.description,.summary,.dek')?.textContent||'';
    const text=` ${title} ${desc} `.toLowerCase();
    if(/\b(breaking|deadly|killed|mass shooting|earthquake|hurricane|wildfire|evacuat(?:e|ion)|airstrike|missile strike|invasion|ceasefire|state of emergency|major outage|data breach|cyberattack)\b/.test(text))return 'red';
    if(/\b(developing|investigation|indict(?:ed|ment)|arrest(?:ed)?|lawsuit|court rules?|strike|shutdown|recall|outbreak|tariffs?|layoffs?|bankruptcy|fraud|charges?)\b/.test(text))return 'orange';
    if(/\b(congress|senate|house of representatives|white house|president|federal|supreme court|legislation|\bbill\b|executive order|election|voters?|governor|policy|regulation|rulemaking)\b/.test(text))return 'purple';
    if(/\b(science|research|study finds?|breakthrough|discovery|health|medical|renewable|education|achievement|award|solution|conservation|recovery)\b/.test(text))return 'green';
    return 'blue';
  }

  function applyRail(card){
    if(!(card instanceof Element))return;
    if(card.classList.contains('underreported-item')||card.classList.contains('nfl-game-card'))return;
    if(activeTabKey()==='boxoffice')return;
    const band=importanceBand(card);
    RAIL_CLASSES.forEach(cls=>card.classList.remove(cls));
    card.classList.add(`rail-${band}`);
    card.dataset.railHierarchy=band;
    card.style.setProperty('border-left',`4px solid ${RAIL_COLORS[band]}`,'important');
  }

  function apply(root=document){
    clearBoxOfficeFeedback(root);
    if(activeTabKey()==='boxoffice'){
      fixBoxOffice(root);
      return;
    }
    if(root instanceof Element&&root.matches('.news-item'))applyRail(root);
    root.querySelectorAll?.('.news-item').forEach(applyRail);
  }

  function start(){
    apply(document);
    const observer=new MutationObserver(mutations=>{
      let relevant=false;
      for(const mutation of mutations){
        if(mutation.type==='childList'&&mutation.addedNodes.length){relevant=true;break;}
        if(mutation.type==='attributes'){relevant=true;break;}
      }
      if(relevant)requestAnimationFrame(()=>apply(document));
    });
    observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','data-category','data-tab']});
    document.addEventListener('click',event=>{
      if(event.target.closest('.tab'))requestAnimationFrame(()=>requestAnimationFrame(()=>apply(document)));
    });
    window.addEventListener('pageshow',()=>apply(document),{passive:true});
    document.documentElement.dataset.uxHotfixV51='ready';
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
