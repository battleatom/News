from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# V2.3 fully replaces the retired minute-polling badge controller.
for tag, marker, close in (
    ('script', 'new-badge-expiry-v1', '</script>'),
    ('script', 'alerts-new-v23', '</script>'),
):
    needle = f'<{tag} id="{marker}">'
    while needle in s:
        a = s.find(needle)
        b = s.find(close, a)
        if b < 0:
            break
        s = s[:a] + s[b + len(close):]

# Route all legacy refresh-time audio requests through the V2.3 event gate.
# This deliberately queues a notification instead of playing immediately.
s = s.replace(
    'if(newCount>0)playNewArticlePop();',
    "if(newCount>0&&typeof window.__queueNewArticlePopV23==='function')window.__queueNewArticlePopV23(newCount);",
)

# V2.2 originally played a test tone when the user enabled alerts. Remove that
# behavior at build time: opting in should be silent, and only a verified new
# story event is allowed to make the audible pop.
s = s.replace(
    "if(ok){try{localStorage.setItem(SOUND_KEY,'on')}catch(e){};if(test)synthPop();}",
    "if(ok){try{localStorage.setItem(SOUND_KEY,'on')}catch(e){}}",
)

SCRIPT = r'''<script id="alerts-new-v23">
(function(){
  'use strict';
  const NEW_TTL=60*60*1000;
  const SERVER_STATS='update-stats.json';
  let serverNewLinks=new Set();
  let serverStatsAt=0;
  let clientNewLinks=new Map();
  let queuedNewCount=0;
  let refreshWrapped=false;

  function normalizeLink(v){
    try{const u=new URL(String(v||''),location.href);u.hash='';return u.href}
    catch(e){return String(v||'').trim()}
  }
  function feedLinks(){
    let items=[];
    try{items=(typeof allItems!=='undefined'&&Array.isArray(allItems))?allItems:(Array.isArray(window.allItems)?window.allItems:[])}catch(e){items=Array.isArray(window.allItems)?window.allItems:[]}
    const out=new Set();
    items.forEach(item=>{const link=normalizeLink(item?.querySelector?.('link')?.textContent||'');if(link)out.add(link)});
    return out;
  }
  function pruneClientNew(){
    const now=Date.now();
    for(const [link,expires] of clientNewLinks){if(expires<=now)clientNewLinks.delete(link)}
  }
  function markClientNew(links){
    const expires=Date.now()+NEW_TTL;
    (links||[]).forEach(link=>{link=normalizeLink(link);if(link)clientNewLinks.set(link,expires)});
    try{sessionStorage.setItem('underreported-client-new-v23',JSON.stringify([...clientNewLinks]))}catch(e){}
  }
  function restoreClientNew(){
    try{
      const rows=JSON.parse(sessionStorage.getItem('underreported-client-new-v23')||'[]');
      if(Array.isArray(rows))rows.forEach(row=>{if(Array.isArray(row)&&row.length===2)clientNewLinks.set(normalizeLink(row[0]),Number(row[1])||0)});
    }catch(e){}
    pruneClientNew();
  }
  function isKnownNew(link){
    link=normalizeLink(link);if(!link)return false;
    pruneClientNew();
    if(clientNewLinks.has(link))return true;
    return Date.now()-serverStatsAt<=NEW_TTL&&serverNewLinks.has(link);
  }
  function decorate(){
    document.querySelectorAll('#news-feed .news-item').forEach(card=>{
      const h=card.querySelector('h3');if(!h)return;
      const href=normalizeLink(card.querySelector('h3 a[href]')?.href||'');
      const fresh=isKnownNew(href);
      const existing=h.querySelector('.new-badge');
      if(fresh&&!existing){
        const badge=document.createElement('span');badge.className='new-badge';badge.textContent='NEW';
        badge.title='Newly discovered by Underreported within the last hour';h.appendChild(badge);
      }else if(!fresh&&existing){existing.remove()}
    });
  }
  window.decorateNewBadges=decorate;
  window.__markNewArticleLinksV23=function(links){markClientNew(links);decorate()};

  async function syncServerNew(){
    try{
      const r=await fetch(SERVER_STATS+'?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);
      const stats=await r.json();
      const at=Date.parse(stats.updatedAt||'')||0;
      serverStatsAt=at;
      serverNewLinks=(at&&Date.now()-at<=NEW_TTL)?new Set((stats.newLinks||[]).map(normalizeLink)):new Set();
    }catch(e){console.warn('V2.3 new-article statistics unavailable:',e)}
    decorate();
  }

  // The older page code may detect a positive newCount while parsing the feed.
  // Queue that fact; do not make sound until the wrapper verifies actual new links.
  window.__queueNewArticlePopV23=function(count){queuedNewCount=Math.max(queuedNewCount,Number(count)||0)};

  function playOnlyForVerifiedNew(count){
    if(!(count>0)||!(queuedNewCount>0))return false;
    queuedNewCount=0;
    if(typeof window.playNewArticlePop==='function')return window.playNewArticlePop();
    return false;
  }

  function wrapRefresh(){
    if(refreshWrapped||typeof window.refreshNewsFromPage!=='function')return;
    const previous=window.refreshNewsFromPage;
    if(previous.__v23Wrapped){refreshWrapped=true;return}
    const wrapped=async function(...args){
      const before=feedLinks();queuedNewCount=0;
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

  // Android/Chrome requires a user gesture to unlock audio. Enabling alerts is
  // intentionally silent; the next verified new-article event is the first pop.
  document.addEventListener('click',function(e){
    const btn=e.target?.closest?.('#sound-alerts-toggle');if(!btn)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(typeof window.enableNewArticleSound==='function')void window.enableNewArticleSound(false);
  },true);

  restoreClientNew();
  wrapRefresh();
  void syncServerNew();
  const feed=document.getElementById('news-feed');
  if(feed)new MutationObserver(decorate).observe(feed,{childList:true,subtree:true});
  document.addEventListener('underreported:feed-rendered',decorate);
  window.__alertsNewV23=true;
})();
</script>'''

if '</body>' not in s:
    raise SystemExit('Generated page is missing </body>')
s = s.replace('</body>', SCRIPT + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Installed V2.3 server-backed NEW badges and verified-new-only audio notifications.')
