from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

MARKER = 'bookmark-persistence-v1'
if MARKER in s:
    print('Bookmark persistence patch already applied.')
    raise SystemExit(0)

old = """  const STORAGE_KEY='news-bookmarks-v1';
  let bookmarkMode=false;
  let bookmarked=new Set(loadBookmarks());
  let rendering=false;

  function loadBookmarks(){
    try{const v=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(v)?v:[];}catch(e){return[];}
  }
  function saveBookmarks(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify([...bookmarked]));}catch(e){}}
"""
new = """  const STORAGE_KEY='news-bookmarks-v1';
  const DATA_KEY='news-bookmark-data-v1';
  let bookmarkMode=false;
  let bookmarked=new Set(loadBookmarks());
  let bookmarkData=loadBookmarkData();
  let rendering=false;

  function loadBookmarks(){
    try{const v=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(v)?v:[];}catch(e){return[];}
  }
  function saveBookmarks(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify([...bookmarked]));}catch(e){}}
  function loadBookmarkData(){
    try{const v=JSON.parse(localStorage.getItem(DATA_KEY)||'{}');return v&&typeof v==='object'?v:{};}catch(e){return{};}
  }
  function saveBookmarkData(){try{localStorage.setItem(DATA_KEY,JSON.stringify(bookmarkData));}catch(e){}}
  function readItem(item){
    return {
      key:itemKey(item),
      title:itemTitle(item),
      link:itemLink(item),
      description:item?.querySelector?.('description')?.textContent||'',
      date:item?.querySelector?.('pubDate')?.textContent||'',
      source:item?.querySelector?.('source')?.textContent||''
    };
  }
  function rememberItem(item){
    if(!item)return;
    const data=readItem(item); if(!data.key)return;
    bookmarkData[data.key]=data; saveBookmarkData();
  }
"""
if old not in s:
    raise SystemExit('Could not locate bookmark storage block')
s=s.replace(old,new,1)

old = """  function renderBookmarks(){
    const root=document.getElementById('news-feed');
    if(!root)return;
    const items=(typeof allItems!=='undefined'?allItems:[]).filter(x=>bookmarked.has(itemKey(x)));
    root.innerHTML='';
"""
new = """  function renderBookmarks(){
    const root=document.getElementById('news-feed');
    if(!root)return;
    const current=(typeof allItems!=='undefined'?allItems:[]);
    current.forEach(x=>{if(bookmarked.has(itemKey(x))) rememberItem(x);});
    const currentByKey={}; current.forEach(x=>{currentByKey[itemKey(x)]=x;});
    const items=[...bookmarked].map(k=>currentByKey[k]||bookmarkData[k]).filter(Boolean);
    root.innerHTML='';
"""
if old not in s:
    raise SystemExit('Could not locate bookmark renderer')
s=s.replace(old,new,1)

old = """      const title=itemTitle(item),link=itemLink(item),desc=item.querySelector('description')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'',source=item.querySelector('source')?.textContent||'';
      ar.dataset.bookmarkKey=itemKey(item);
"""
new = """      const isStored=typeof item==='object' && typeof item.querySelector!=='function';
      const title=isStored?(item.title||'Untitled'):itemTitle(item);
      const link=isStored?(item.link||'#'):itemLink(item);
      const desc=isStored?(item.description||''):item.querySelector('description')?.textContent||'';
      const date=isStored?(item.date||''):item.querySelector('pubDate')?.textContent||'';
      const source=isStored?(item.source||''):item.querySelector('source')?.textContent||'';
      const storedKey=isStored?(item.key||''):itemKey(item);
      ar.dataset.bookmarkKey=storedKey;
"""
if old not in s:
    raise SystemExit('Could not locate bookmark item fields')
s=s.replace(old,new,1)

old = """      ar.querySelector('.bookmark-btn').addEventListener('click',()=>{bookmarked.delete(itemKey(item));saveBookmarks();updateBookmarkTab();renderBookmarks();});
"""
new = """      ar.querySelector('.bookmark-btn').addEventListener('click',()=>{const k=isStored?(item.key||''):itemKey(item);bookmarked.delete(k);delete bookmarkData[k];saveBookmarks();saveBookmarkData();updateBookmarkTab();renderBookmarks();});
"""
if old not in s:
    raise SystemExit('Could not locate bookmark removal handler')
s=s.replace(old,new,1)

old = """      btn.addEventListener('click',e=>{
        e.preventDefault(); e.stopPropagation();
        if(bookmarked.has(key))bookmarked.delete(key);else bookmarked.add(key);
        saveBookmarks();
"""
new = """      btn.addEventListener('click',e=>{
        e.preventDefault(); e.stopPropagation();
        if(bookmarked.has(key)){bookmarked.delete(key);delete bookmarkData[key];}
        else{bookmarked.add(key);if(typeof allItems!=='undefined'){const item=allItems.find(x=>itemKey(x)===key);if(item)rememberItem(item);}}
        saveBookmarks(); saveBookmarkData();
"""
if old not in s:
    raise SystemExit('Could not locate bookmark toggle handler')
s=s.replace(old,new,1)

old = """  function start(){
    ensureBookmarkTab();
"""
new = """  function start(){
    // Migrate any currently visible bookmarks into durable article records.
    if(typeof allItems!=='undefined') allItems.forEach(x=>{if(bookmarked.has(itemKey(x))) rememberItem(x);});
    ensureBookmarkTab();
"""
if old not in s:
    raise SystemExit('Could not locate bookmark start function')
s=s.replace(old,new,1)

# Stamp the installed script so this patch is not reapplied.
s=s.replace("<script id=\"bookmarks-v1\">", "<script id=\"bookmarks-v1\">\\n/* bookmark-persistence-v1 */", 1)
P.write_text(s,encoding='utf-8')
print('Installed bookmark-persistence-v1: bookmarked articles retain their saved title/link/content metadata even after leaving the live feed.')
