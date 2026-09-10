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
for tag, marker, close in (
    ('script', 'load-more-v1', '</script>'),
    ('style', 'load-more-style-v1', '</style>'),
):
    needle = f'<{tag} id="{marker}">'
    while needle in text:
        start = text.find(needle)
        end = text.find(close, start)
        if end < 0:
            break
        text = text[:start] + text[end + len(close):]

text = text.replace(
    'allNfl.slice(0,10).forEach((item,i)=>',
    'allNfl.slice(0,Math.min((window.loadCounts?.nfl||10),allNfl.length)).forEach((item,i)=>',
    1,
)

style = r'''<style id="load-more-style-v1">
.load-more-wrap{display:flex;justify-content:center;width:100%;padding:18px 12px 8px;box-sizing:border-box}
.load-more{appearance:none;border:1px solid #cbd5e1;border-radius:999px;background:#fff;color:#0f172a;padding:11px 20px;font:inherit;font-size:12px;font-weight:800;cursor:pointer;box-shadow:0 2px 8px rgba(15,23,42,.08)}
.load-more:active{transform:translateY(1px)}
.news-item[data-page-hidden="true"]{display:none!important}
</style>'''
text = text.replace('</head>', style + '\n</head>', 1)

script = r'''<script id="load-more-v1">
const STORIES_PER_PAGE = 10;
const TOP_SEEN_STORAGE = 'news-top-seen-v1';
window.loadCounts = window.loadCounts || {};
const loadCounts = window.loadCounts;
window.topRotationKeys = window.topRotationKeys || [];

function topStoryKey(item){
  const link=(item.querySelector('link')?.textContent||'').trim().toLowerCase().replace(/[?#].*$/,'').replace(/\/$/,'');
  if(link)return 'l:'+link;
  const title=(item.querySelector('title')?.textContent||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  return 't:'+title;
}
function topStorageDay(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function readTopSeen(){try{const raw=JSON.parse(localStorage.getItem(TOP_SEEN_STORAGE)||'{}');if(raw.day!==topStorageDay()||!Array.isArray(raw.keys))return new Set();return new Set(raw.keys)}catch(e){return new Set()}}
function writeTopSeen(seen){try{localStorage.setItem(TOP_SEEN_STORAGE,JSON.stringify({day:topStorageDay(),keys:[...seen].slice(-300)}))}catch(e){}}
function topItemsNewestFirst(items){return items.map((item,index)=>({item,index})).filter(x=>(x.item.querySelector('category')?.textContent?.trim()||'world')==='top').sort((a,b)=>{const ad=Date.parse(a.item.querySelector('pubDate')?.textContent||'')||0;const bd=Date.parse(b.item.querySelector('pubDate')?.textContent||'')||0;return bd-ad||a.index-b.index}).map(x=>x.item)}
function topItemIsFresh(item){const ms=Date.parse(item.querySelector('pubDate')?.textContent||'');return Number.isFinite(ms)&&Date.now()-ms<=60*60*1000&&Date.now()>=ms-5*60*1000}
function topDisplayItems(items){
  const ordered=topItemsNewestFirst(items),seen=readTopSeen(),byKey=new Map(ordered.map(item=>[topStoryKey(item),item]));
  const freshUnseen=ordered.filter(item=>!seen.has(topStoryKey(item))&&topItemIsFresh(item));
  const freshKeys=new Set(freshUnseen.map(topStoryKey));
  const rotated=(window.topRotationKeys||[]).map(k=>byKey.get(k)).filter(Boolean).filter(item=>!freshKeys.has(topStoryKey(item)));
  const used=new Set([...freshUnseen,...rotated].map(topStoryKey));
  return [...freshUnseen,...rotated,...ordered.filter(item=>!used.has(topStoryKey(item)))];
}
function markTopStoriesSeen(items){const seen=readTopSeen();items.forEach(item=>seen.add(topStoryKey(item)));writeTopSeen(seen)}
function syncDiscoveryButton(){if(typeof window.syncTopDiscoveryButton==='function')window.syncTopDiscoveryButton()}
function categoryData(items){
  let available;
  if(active==='top')available=topDisplayItems(items);
  else{
    const categoryItems=items.filter(item=>(item.querySelector('category')?.textContent?.trim()||'world')===active);
    available=categoryItems;
    if(active==='region')available=categoryItems.filter(item=>(item.querySelector('region')?.textContent?.trim()||'')===detectedRegion);
  }
  return {available,count:Math.min(loadCounts[active]||STORIES_PER_PAGE,available.length)};
}
function renderedData(){
  const root=document.getElementById('news-feed');
  const cards=root?[...root.querySelectorAll('.section-body .news-item')]:[];
  return {available:cards,count:Math.min(loadCounts[active]||STORIES_PER_PAGE,cards.length)};
}
function applyVisibleCount(data){
  const root=document.getElementById('news-feed');if(!root)return;
  const cards=[...root.querySelectorAll('.section-body .news-item')];
  const total=cards.length;
  const count=Math.min(data.count,total);
  cards.forEach((card,i)=>{if(i<count)card.removeAttribute('data-page-hidden');else card.setAttribute('data-page-hidden','true')});
  const countEl=root.querySelector('.section .section-header .count');
  if(countEl)countEl.textContent=`Showing ${count} of ${total} stories`;
  root.querySelectorAll('.load-more-wrap').forEach(el=>el.remove());
  if(total<=count)return;
  const wrap=document.createElement('div');wrap.className='load-more-wrap';
  const button=document.createElement('button');button.type='button';button.className='load-more';
  const next=Math.min(count+STORIES_PER_PAGE,total);
  button.textContent=`Load 10 more (${next} of ${total})`;
  button.addEventListener('click',e=>{
    e.preventDefault();e.stopPropagation();
    const y=window.scrollY,key=active;
    loadCounts[key]=next;
    applyVisibleCount({count:next});
    if(active===key&&Math.abs(window.scrollY-y)>2)window.scrollTo({top:y,left:window.scrollX,behavior:'auto'});
  });
  wrap.appendChild(button);root.appendChild(wrap);
}

const baseCanonicalRenderWithPagination=canonicalRender;
canonicalRender=function(items){
  if(active==='bookmarks'||active==='boxoffice'){
    const out=baseCanonicalRenderWithPagination(items);syncDiscoveryButton();return out;
  }
  // These tabs have specialized renderers that derive/merge records from multiple
  // categories. They must receive the complete feed, then pagination is applied to
  // the cards they actually rendered.
  if(active==='nfl'||active==='legislation'||active==='nm'){
    baseCanonicalRenderWithPagination(items);
    const data=renderedData();
    applyVisibleCount(data);
    syncDiscoveryButton();
    return;
  }
  const data=categoryData(items);
  baseCanonicalRenderWithPagination(data.available);
  applyVisibleCount(renderedData());
  if(active==='top')markTopStoriesSeen(data.available.slice(0,data.count));
  syncDiscoveryButton();
};

window.cycleTopStoriesAndRefresh=async function(){
  if(active!=='top')return false;
  const ordered=topItemsNewestFirst(allItems),seen=readTopSeen(),unseen=ordered.filter(item=>!seen.has(topStoryKey(item)));
  const status=document.getElementById('status');
  if(unseen.length){window.topRotationKeys=unseen.slice(0,STORIES_PER_PAGE).map(topStoryKey);if(status)status.textContent='Showing unseen Top Stories · checking for updates…'}
  else{window.topRotationKeys=[];if(status)status.textContent='You’re caught up · showing newest Top Stories · checking for updates…'}
  loadCounts.top=STORIES_PER_PAGE;canonicalRender(allItems);
  const refreshFn=window.refreshNewsFromPage||(typeof refreshNewsFromPage==='function'?refreshNewsFromPage:null);
  if(refreshFn){try{await refreshFn(false)}catch(e){console.error('Passive full-feed refresh failed:',e)}}
  return true;
};

render=canonicalRender;window.render=canonicalRender;
syncDiscoveryButton();
window.__loadMoreRevealOnlyV282=true;
</script>'''

text = text.replace('</body>', script + '\n</body>', 1)
INDEX.write_text(text, encoding="utf-8")
print("Applied reveal-only Load More pagination with specialized renderer preservation.")
