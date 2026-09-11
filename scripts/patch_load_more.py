from pathlib import Path

INDEX = Path("index.html")
UPDATE = Path("scripts/update_news.py")

text = UPDATE.read_text(encoding="utf-8")
text = text.replace(
    'if len(selected) == 10:\n            break\n    return selected\n\n\ndef select_underreported',
    'if len(selected) == 30:\n            break\n    return selected\n\n\ndef select_underreported',
    1,
)
text = text.replace(
    'if len(selected) == 12:\n            break\n    return selected\n\n\ndef select_category_stories(items, limit=10):',
    'if len(selected) == 30:\n            break\n    return selected\n\n\ndef select_category_stories(items, limit=30):',
    1,
)
text = text.replace(
    '"""Select up to 10 distinct stories, with Local queries treated as the geographic scope."""',
    '"""Select up to 30 distinct stories, with Local queries treated as the geographic scope."""',
    1,
)
text = text.replace('select_category_stories(region_items, limit=10)', 'select_category_stories(region_items, limit=30)', 1)
UPDATE.write_text(text, encoding="utf-8")

text = INDEX.read_text(encoding="utf-8")
marker = '<script id="load-more-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</script>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</script>'):]

style_marker = '<style id="load-more-style-v1">'
while style_marker in text:
    start = text.find(style_marker)
    end = text.find('</style>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</style>'):]

# The live NFL renderer is installed immediately before this patch and used to
# hard-limit itself to 10 stories. Make it honor the same count as pagination.
text = text.replace(
    'allNfl.slice(0,10).forEach((item,i)=>',
    'allNfl.slice(0,Math.min((window.loadCounts?.nfl||10),allNfl.length)).forEach((item,i)=>',
    1,
)

# One canonical pagination router owns category paging and infinite scrolling.
# Later feature modules register category-specific renderers instead of wrapping
# canonicalRender again, keeping the render chain deterministic.
script = r'''<script id="load-more-v1">
const STORIES_PER_PAGE = 10;
const TOP_DISCOVERY_MARKER = 'top-story-cycle-v1';
const TOP_SEEN_STORAGE = 'news-top-seen-v1';
window.loadCounts = window.loadCounts || {};
const loadCounts = window.loadCounts;
window.topRotationKeys = window.topRotationKeys || [];
window.__categoryRenderers = window.__categoryRenderers || {};

function topStoryKey(item){
  const link=(item.querySelector('link')?.textContent||'').trim().toLowerCase().replace(/[?#].*$/,'').replace(/\/$/,'');
  if(link)return 'l:'+link;
  const title=(item.querySelector('title')?.textContent||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  return 't:'+title;
}
function topStorageDay(){
  const d=new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function readTopSeen(){
  try{
    const raw=JSON.parse(localStorage.getItem(TOP_SEEN_STORAGE)||'{}');
    if(raw.day!==topStorageDay()||!Array.isArray(raw.keys))return new Set();
    return new Set(raw.keys);
  }catch(e){return new Set()}
}
function writeTopSeen(seen){
  try{localStorage.setItem(TOP_SEEN_STORAGE,JSON.stringify({day:topStorageDay(),keys:[...seen].slice(-300)}))}catch(e){}
}
function topItemsNewestFirst(items){
  return items
    .map((item,index)=>({item,index}))
    .filter(x=>(x.item.querySelector('category')?.textContent?.trim()||'world')==='top')
    .sort((a,b)=>{
      const ad=Date.parse(a.item.querySelector('pubDate')?.textContent||'')||0;
      const bd=Date.parse(b.item.querySelector('pubDate')?.textContent||'')||0;
      return bd-ad||a.index-b.index;
    })
    .map(x=>x.item);
}
function topItemIsFresh(item){
  const ms=Date.parse(item.querySelector('pubDate')?.textContent||'');
  return Number.isFinite(ms)&&Date.now()-ms<=60*60*1000&&Date.now()>=ms-5*60*1000;
}
function topDisplayItems(items){
  const ordered=topItemsNewestFirst(items);
  const seen=readTopSeen();
  const byKey=new Map(ordered.map(item=>[topStoryKey(item),item]));
  const freshUnseen=ordered.filter(item=>!seen.has(topStoryKey(item))&&topItemIsFresh(item));
  const freshKeys=new Set(freshUnseen.map(topStoryKey));
  const rotated=(window.topRotationKeys||[]).map(k=>byKey.get(k)).filter(Boolean).filter(item=>!freshKeys.has(topStoryKey(item)));
  const used=new Set([...freshUnseen,...rotated].map(topStoryKey));
  return [...freshUnseen,...rotated,...ordered.filter(item=>!used.has(topStoryKey(item)))];
}
function markTopStoriesSeen(items){
  const seen=readTopSeen();
  items.forEach(item=>seen.add(topStoryKey(item)));
  writeTopSeen(seen);
}
function syncDiscoveryButton(){
  if(typeof window.syncTopDiscoveryButton==='function')window.syncTopDiscoveryButton();
}

function paginatedNewsItems(items){
  let available;
  if(active==='top'){
    available=topDisplayItems(items);
  }else{
    const categoryItems=items.filter(item=>(item.querySelector('category')?.textContent?.trim()||'world')===active);
    available=categoryItems;
    if(active==='region')available=categoryItems.filter(item=>(item.querySelector('region')?.textContent?.trim()||'')===detectedRegion);
  }
  const count=Math.min(loadCounts[active]||STORIES_PER_PAGE,available.length);
  return {available,visible:available.slice(0,count),count};
}

function appendLoadMoreControl(data){
  const root=document.getElementById('news-feed');
  if(!root)return;
  root.querySelectorAll('.load-more-wrap,.infinite-scroll-sentinel').forEach(el=>el.remove());
  if(window.__infiniteScrollObserver){
    try{window.__infiniteScrollObserver.disconnect()}catch(e){}
    window.__infiniteScrollObserver=null;
  }
  if(data.available.length<=data.count)return;

  const sentinel=document.createElement('div');
  sentinel.className='infinite-scroll-sentinel';
  sentinel.setAttribute('aria-hidden','true');
  sentinel.style.cssText='height:1px;width:100%;margin-top:8px;';
  root.appendChild(sentinel);

  let loading=false;
  const observer=new IntersectionObserver(entries=>{
    if(loading||!entries.some(entry=>entry.isIntersecting))return;
    loading=true;
    observer.disconnect();

    const cards=[...document.querySelectorAll('#news-feed .news-item')];
    const anchor=cards[cards.length-1]||null;
    const anchorHref=anchor?.querySelector('h3 a[href]')?.href||'';
    const anchorTop=anchor?.getBoundingClientRect().top??null;
    const next=Math.min((loadCounts[active]||STORIES_PER_PAGE)+STORIES_PER_PAGE,data.available.length);
    loadCounts[active]=next;
    canonicalRender(allItems);

    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(anchorHref&&anchorTop!==null){
        const replacement=[...document.querySelectorAll('#news-feed .news-item h3 a[href]')]
          .find(a=>a.href===anchorHref)?.closest('.news-item');
        if(replacement){
          const delta=replacement.getBoundingClientRect().top-anchorTop;
          if(Math.abs(delta)>1)window.scrollBy({top:delta,left:0,behavior:'auto'});
        }
      }
      loading=false;
    }));
  },{root:null,rootMargin:'700px 0px 700px 0px',threshold:0.01});

  window.__infiniteScrollObserver=observer;
  observer.observe(sentinel);
}

const baseCanonicalRenderWithPagination=canonicalRender;
canonicalRender=function(items){
  if(active==='bookmarks'||active==='boxoffice'){
    const out=baseCanonicalRenderWithPagination(items);
    syncDiscoveryButton();
    return out;
  }

  const customRenderer=window.__categoryRenderers?.[active];
  if(typeof customRenderer==='function'){
    const out=customRenderer(items);
    syncDiscoveryButton();
    return out;
  }

  if(active==='nfl'){
    const data=paginatedNewsItems(items);
    loadCounts.nfl=data.count;
    baseCanonicalRenderWithPagination(items);
    const nflHeaders=[...document.querySelectorAll('.section-header')];
    const nflNewsHeader=nflHeaders.find(el=>el.querySelector('h2')?.textContent?.trim()==='NFL News');
    const countEl=nflNewsHeader?.querySelector('.count');
    if(countEl)countEl.textContent=`Showing ${data.count} of ${data.available.length}`;
    appendLoadMoreControl(data);
    syncDiscoveryButton();
    return;
  }

  const data=paginatedNewsItems(items);
  baseCanonicalRenderWithPagination(data.visible);
  const root=document.getElementById('news-feed');
  const countEl=root?.querySelector('.section .section-header .count');
  if(countEl)countEl.textContent=`Showing ${data.count} of ${data.available.length} stories`;
  if(active==='top')markTopStoriesSeen(data.visible);
  appendLoadMoreControl(data);
  syncDiscoveryButton();
};

window.cycleTopStoriesAndRefresh=async function(){
  if(active!=='top')return false;
  const ordered=topItemsNewestFirst(allItems);
  const seen=readTopSeen();
  const unseen=ordered.filter(item=>!seen.has(topStoryKey(item)));
  const status=document.getElementById('status');
  if(unseen.length){
    const batch=unseen.slice(0,STORIES_PER_PAGE);
    window.topRotationKeys=batch.map(topStoryKey);
    loadCounts.top=STORIES_PER_PAGE;
    canonicalRender(allItems);
    if(status)status.textContent=`Showing ${batch.length} unseen Top Stories · checking for updates…`;
  }else{
    window.topRotationKeys=[];
    loadCounts.top=STORIES_PER_PAGE;
    canonicalRender(allItems);
    if(status)status.textContent='You’re caught up · showing newest Top Stories · checking for updates…';
  }
  const refreshFn=window.refreshNewsFromPage||(typeof refreshNewsFromPage==='function'?refreshNewsFromPage:null);
  if(refreshFn){
    try{await refreshFn(false)}catch(e){console.error('Passive full-feed refresh failed:',e)}
  }
  return true;
};

render=canonicalRender;
window.render=canonicalRender;
window.canonicalRender=canonicalRender;
syncDiscoveryButton();
</script>'''

text = text.replace('</body>', script + '\n</body>', 1)
INDEX.write_text(text, encoding="utf-8")
print("Installed one canonical pagination router with anchored infinite scrolling and custom category renderers.")
