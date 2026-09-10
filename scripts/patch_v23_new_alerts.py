from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Replace prior NEW controllers and the V2.6 badge color override idempotently.
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

# Older refresh code can report a count, but only the verified before/after link
# comparison below may make an automatic notification sound. The V2.2 sound
# control remains the single owner of user-initiated enable/test clicks.
s = s.replace(
    'if(newCount>0)playNewArticlePop();',
    "if(newCount>0&&typeof window.__queueNewArticlePopV23==='function')window.__queueNewArticlePopV23(newCount);",
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
  const RED_SITE_TTL=60*60*1000;
  const BLUE_PUBLISHED_TTL=3*60*60*1000;
  const YELLOW_SITE_TTL=3*60*60*1000;
  const YELLOW_MIN_PUBLISHED_AGE=6*60*60*1000;
  const CLOCK_SLOP=5*60*1000;
  const SERVER_STATS='update-stats.json';
  const CLIENT_KEY='underreported-first-seen-v26';
  let serverFirstSeen=new Map();
  let clientFirstSeen=new Map();
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
  function pruneClient(){
    const cutoff=Date.now()-YELLOW_SITE_TTL;
    for(const [link,at] of clientFirstSeen){if(!Number.isFinite(at)||at<cutoff)clientFirstSeen.delete(link)}
  }
  function saveClient(){
    pruneClient();
    try{localStorage.setItem(CLIENT_KEY,JSON.stringify([...clientFirstSeen]))}catch(e){}
  }
  function restoreClient(){
    try{
      const rows=JSON.parse(localStorage.getItem(CLIENT_KEY)||'[]');
      if(Array.isArray(rows))rows.forEach(row=>{if(Array.isArray(row)&&row.length===2)clientFirstSeen.set(normalizeLink(row[0]),Number(row[1])||0)});
    }catch(e){}
    pruneClient();
  }
  function markClientNew(links){
    const now=Date.now();
    (links||[]).forEach(raw=>{
      const link=normalizeLink(raw);if(!link)return;
      if(!clientFirstSeen.has(link)&&!serverFirstSeen.has(link))clientFirstSeen.set(link,now);
    });
    saveClient();
  }
  function firstSeenFor(link){
    link=normalizeLink(link);if(!link)return 0;
    const server=Number(serverFirstSeen.get(link)||0);if(server)return server;
    pruneClient();return Number(clientFirstSeen.get(link)||0);
  }
  function classifyTimes(publishedAt,firstSeenAt,now=Date.now()){
    const pub=Number(publishedAt)||0,first=Number(firstSeenAt)||0;
    const siteAge=first?now-first:Infinity;
    const pubAge=pub?now-pub:Infinity;
    if(first&&siteAge>=-CLOCK_SLOP&&siteAge<=RED_SITE_TTL)return 'red';
    if(pub&&pubAge>=-CLOCK_SLOP&&pubAge<=BLUE_PUBLISHED_TTL)return 'blue';
    if(first&&siteAge>=-CLOCK_SLOP&&siteAge<=YELLOW_SITE_TTL&&pub&&pubAge>YELLOW_MIN_PUBLISHED_AGE)return 'yellow';
    return '';
  }
  window.__classifyNewBadgeV26=classifyTimes;

  function scheduleNextChange(pub,first,now){
    const points=[];
    if(first){points.push(first+RED_SITE_TTL,first+YELLOW_SITE_TTL)}
    if(pub)points.push(pub+BLUE_PUBLISHED_TTL);
    return points.filter(x=>x>now+250).sort((a,b)=>a-b)[0]||0;
  }
  function decorate(){
    const pubs=publicationMap(),now=Date.now();let next=0;
    document.querySelectorAll('#news-feed .news-item').forEach(card=>{
      const h=card.querySelector('h3');if(!h)return;
      const href=normalizeLink(card.querySelector('h3 a[href]')?.href||'');
      const first=firstSeenFor(href),pub=pubs.get(href)||0;
      const state=classifyTimes(pub,first,now);
      let badge=h.querySelector('.new-badge');
      if(!state){if(badge)badge.remove();return}
      if(!badge){badge=document.createElement('span');badge.className='new-badge';badge.textContent='NEW';h.appendChild(badge)}
      badge.classList.remove('new-badge-red','new-badge-blue','new-badge-yellow');
      badge.classList.add('new-badge-'+state);
      if(state==='red')badge.title='New to Underreported within the last hour';
      if(state==='blue')badge.title='Published within the last three hours';
      if(state==='yellow')badge.title='Older article newly added to Underreported within the last three hours';
      const change=scheduleNextChange(pub,first,now);if(change&&(!next||change<next))next=change;
    });
    if(badgeTimer)clearTimeout(badgeTimer);
    if(next)badgeTimer=setTimeout(decorate,Math.max(500,next-Date.now()+100));
  }
  window.decorateNewBadges=decorate;
  window.__markNewArticleLinksV23=function(links){markClientNew(links);decorate()};

  async function syncServerNew(){
    try{
      const r=await fetch(SERVER_STATS+'?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);
      const stats=await r.json();
      const map=new Map();
      if(stats.firstSeenAt&&typeof stats.firstSeenAt==='object'){
        Object.entries(stats.firstSeenAt).forEach(([raw,stamp])=>{const link=normalizeLink(raw),at=Date.parse(stamp)||Number(stamp)||0;if(link&&at)map.set(link,at)});
      }else{
        const at=Date.parse(stats.updatedAt||'')||0;
        (stats.newLinks||[]).forEach(raw=>{const link=normalizeLink(raw);if(link&&at)map.set(link,at)});
      }
      serverFirstSeen=map;
    }catch(e){console.warn('NEW article statistics unavailable:',e)}
    decorate();
  }

  window.__queueNewArticlePopV23=function(count){return Number(count)||0};
  function playOnlyForVerifiedNew(count){
    if(!(count>0))return false;
    if(typeof window.playNewArticlePop==='function')return window.playNewArticlePop();
    return false;
  }
  window.__playVerifiedNewV23=playOnlyForVerifiedNew;

  function wrapRefresh(){
    if(refreshWrapped||typeof window.refreshNewsFromPage!=='function')return;
    const previous=window.refreshNewsFromPage;
    if(previous.__v23Wrapped){refreshWrapped=true;return}
    const wrapped=async function(...args){
      const before=feedLinks();
      const result=await previous.apply(this,args);
      const after=feedLinks();
      const discovered=[...after].filter(link=>!before.has(link));
      if(discovered.length)markClientNew(discovered);
      await syncServerNew();
      decorate();
      playOnlyForVerifiedNew(discovered.length);
      return result;
    };
    wrapped.__v23Wrapped=true;
    window.refreshNewsFromPage=wrapped;
    refreshWrapped=true;
  }

  restoreClient();wrapRefresh();void syncServerNew();
  const feed=document.getElementById('news-feed');
  if(feed)new MutationObserver(decorate).observe(feed,{childList:true,subtree:true});
  document.addEventListener('underreported:feed-rendered',decorate);
  window.__alertsNewV23=true;
  window.__alertsNewV26=true;
})();
</script>'''

if '</body>' not in s:
    raise SystemExit('Generated page is missing </body>')
s = s.replace('</body>', SCRIPT + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Installed V2.6 red/blue/yellow NEW badges with persistent site first-seen timing and verified-new-only audio.')
