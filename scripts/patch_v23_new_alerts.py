from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Replace prior NEW controllers and badge color overrides idempotently.
for tag, marker, close in (
    ('script', 'new-badge-expiry-v1', '</script>'),
    ('script', 'alerts-new-v23', '</script>'),
    ('style', 'new-badge-v26-style', '</style>'),
):
    needle = f'<{tag} id="{marker}">'
    while needle in s:
        a = s.find(needle)
        b = s.find(close, a)
        if b < 0:
            break
        s = s[:a] + s[b + len(close):]

# Older refresh code can report a count, but only the verified fresh-link gate
# below may make a notification sound.
s = s.replace(
    'if(newCount>0)playNewArticlePop();',
    "if(newCount>0&&typeof window.__queueNewArticlePopV23==='function')window.__queueNewArticlePopV23(newCount);",
)
s = s.replace(
    "if(ok){try{localStorage.setItem(SOUND_KEY,'on')}catch(e){};if(test)synthPop();}",
    "if(ok){try{localStorage.setItem(SOUND_KEY,'on')}catch(e){};if(test)synthPop();}",
)

STYLE = r'''<style id="new-badge-v26-style">
.new-badge.new-badge-red{background:#dc2626!important;color:#fff!important}
.new-badge.new-badge-blue{background:#2563eb!important;color:#fff!important}
.new-badge.new-badge-yellow{background:#facc15!important;color:#422006!important}
</style>'''
if '</head>' not in s:
    raise SystemExit('Generated page is missing </head>')
s = s.replace('</head>', STYLE + '\n</head>', 1)

SCRIPT = r'''<script id="alerts-new-v23">
(function(){
  'use strict';
  const RED_TTL=60*60*1000;
  const BLUE_TTL=3*60*60*1000;
  const YELLOW_TTL=6*60*60*1000;
  const AUDIO_TTL=30*60*1000;
  const CLOCK_SLOP=5*60*1000;
  const ALERTED_KEY='underreported-audio-alerted-v281';
  let refreshWrapped=false;
  let badgeTimer=0;

  function normalizeLink(v){
    try{const u=new URL(String(v||''),location.href);u.hash='';return u.href}
    catch(e){return String(v||'').trim()}
  }
  function feedItems(){
    try{return (typeof allItems!=='undefined'&&Array.isArray(allItems))?allItems:(Array.isArray(window.allItems)?window.allItems:[])}catch(e){return Array.isArray(window.allItems)?window.allItems:[]}
  }
  function feedLinks(){
    const out=new Set();
    feedItems().forEach(item=>{const link=normalizeLink(item?.querySelector?.('link')?.textContent||'');if(link)out.add(link)});
    return out;
  }
  function publicationMap(){
    const out=new Map();
    feedItems().forEach(item=>{
      const link=normalizeLink(item?.querySelector?.('link')?.textContent||'');
      const pub=Date.parse(item?.querySelector?.('pubDate')?.textContent||'')||0;
      if(link)out.set(link,pub);
    });
    return out;
  }
  function classifyTimes(publishedAt,_firstSeenAt,now=Date.now()){
    const pub=Number(publishedAt)||0;
    if(!pub)return '';
    const age=now-pub;
    if(age<-CLOCK_SLOP)return '';
    if(age<=RED_TTL)return 'red';
    if(age<=BLUE_TTL)return 'blue';
    if(age<=YELLOW_TTL)return 'yellow';
    return '';
  }
  window.__classifyNewBadgeV26=classifyTimes;

  function scheduleNextChange(pub,now){
    if(!pub)return 0;
    return [pub+RED_TTL,pub+BLUE_TTL,pub+YELLOW_TTL].filter(x=>x>now+250).sort((a,b)=>a-b)[0]||0;
  }
  function decorate(){
    const pubs=publicationMap(),now=Date.now();let next=0;
    document.querySelectorAll('#news-feed .news-item').forEach(card=>{
      const h=card.querySelector('h3');if(!h)return;
      const href=normalizeLink(card.querySelector('h3 a[href]')?.href||'');
      const pub=pubs.get(href)||0;
      const state=classifyTimes(pub,0,now);
      let badge=h.querySelector('.new-badge');
      if(!state){if(badge)badge.remove();return}
      if(!badge){badge=document.createElement('span');badge.className='new-badge';badge.textContent='NEW';h.appendChild(badge)}
      badge.classList.remove('new-badge-red','new-badge-blue','new-badge-yellow');
      badge.classList.add('new-badge-'+state);
      if(state==='red')badge.title='Published within the last hour';
      if(state==='blue')badge.title='Published 1–3 hours ago';
      if(state==='yellow')badge.title='Published 3–6 hours ago';
      const change=scheduleNextChange(pub,now);if(change&&(!next||change<next))next=change;
    });
    if(badgeTimer)clearTimeout(badgeTimer);
    if(next)badgeTimer=setTimeout(decorate,Math.max(500,next-Date.now()+100));
  }
  window.decorateNewBadges=decorate;
  // Kept for compatibility with older callers. Fetch/first-seen state no longer
  // changes badge color; publication time is the only source of badge age.
  window.__markNewArticleLinksV23=function(){decorate()};
  window.__queueNewArticlePopV23=function(count){return Number(count)||0};

  function readAlerted(){
    try{const rows=JSON.parse(localStorage.getItem(ALERTED_KEY)||'[]');return new Set(Array.isArray(rows)?rows:[])}catch(e){return new Set()}
  }
  function saveAlerted(set){try{localStorage.setItem(ALERTED_KEY,JSON.stringify([...set].slice(-500)))}catch(e){}}
  function freshPublishedLinks(links,now=Date.now()){
    const pubs=publicationMap(),alerted=readAlerted(),fresh=[];
    (links||[]).forEach(raw=>{
      const link=normalizeLink(raw),pub=pubs.get(link)||0,age=pub?now-pub:Infinity;
      if(link&&pub&&age>=-CLOCK_SLOP&&age<=AUDIO_TTL&&!alerted.has(link))fresh.push(link);
    });
    return fresh;
  }
  function playFreshPublishedAlert(links){
    const fresh=freshPublishedLinks(links);
    if(!fresh.length)return false;
    const alerted=readAlerted();fresh.forEach(link=>alerted.add(link));saveAlerted(alerted);
    if(typeof window.playNewArticlePop==='function')return window.playNewArticlePop();
    return false;
  }
  window.__freshPublishedLinksV281=freshPublishedLinks;
  window.__playFreshPublishedAlertV281=playFreshPublishedAlert;
  window.__playVerifiedNewV23=function(count){return Number(count)>0?false:false};

  function wrapRefresh(){
    if(refreshWrapped||typeof window.refreshNewsFromPage!=='function')return;
    const previous=window.refreshNewsFromPage;
    if(previous.__v281Wrapped){refreshWrapped=true;return}
    const wrapped=async function(...args){
      const before=feedLinks();
      const result=await previous.apply(this,args);
      const after=feedLinks();
      const discovered=[...after].filter(link=>!before.has(link));
      decorate();
      // Exactly one chime per refresh, and only when at least one newly discovered
      // article was actually published within the last 30 minutes.
      playFreshPublishedAlert(discovered);
      return result;
    };
    wrapped.__v23Wrapped=true;wrapped.__v281Wrapped=true;
    window.refreshNewsFromPage=wrapped;
    refreshWrapped=true;
  }

  document.addEventListener('click',function(e){
    const btn=e.target?.closest?.('#sound-alerts-toggle');if(!btn)return;
    e.preventDefault();e.stopImmediatePropagation();
    // Give the user an audible confirmation when turning sound on so the control
    // has immediate, testable feedback on mobile browsers.
    if(typeof window.enableNewArticleSound==='function')void window.enableNewArticleSound(true);
  },true);

  wrapRefresh();decorate();
  const feed=document.getElementById('news-feed');
  if(feed)new MutationObserver(decorate).observe(feed,{childList:true});
  document.addEventListener('underreported:feed-rendered',decorate);
  window.__alertsNewV23=true;
  window.__alertsNewV26=true;
  window.__alertsNewV281=true;
})();
</script>'''

if '</body>' not in s:
    raise SystemExit('Generated page is missing </body>')
s = s.replace('</body>', SCRIPT + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Installed V2.8.1 publication-age NEW badges and once-per-fresh-article audio alerts.')
