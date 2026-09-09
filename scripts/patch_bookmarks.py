from pathlib import Path

P = Path('index.html')
SCRIPT_ID = 'bookmarks-v1'
MARKER = f'<script id="{SCRIPT_ID}">'

SCRIPT = r'''<script id="bookmarks-v1">
(function(){
  'use strict';
  const STORAGE_KEY='news-bookmarks-v1';
  let bookmarkMode=false;
  let bookmarked=new Set(loadBookmarks());
  let rendering=false;

  function loadBookmarks(){
    try{const v=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(v)?v:[];}catch(e){return[];}
  }
  function saveBookmarks(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify([...bookmarked]));}catch(e){}}
  function itemKey(item){
    const link=(item?.querySelector?.('link')?.textContent||'').trim().toLowerCase().replace(/[?#].*$/,'').replace(/\/$/,'');
    if(link)return 'l:'+link;
    const title=(item?.querySelector?.('title')?.textContent||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
    return 't:'+title;
  }
  function itemTitle(item){return (item?.querySelector?.('title')?.textContent||'Untitled').trim();}
  function itemLink(item){return (item?.querySelector?.('link')?.textContent||'#').trim();}
  function escapeHtml(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}

  function ensureBookmarkTab(){
    const tabs=document.getElementById('tabs');
    if(!tabs)return;
    let b=document.getElementById('bookmarks-tab');
    if(!b){
      b=document.createElement('button');
      b.id='bookmarks-tab'; b.className='tab'; b.type='button';
      b.textContent=`🔖 Bookmarks (${bookmarked.size})`;
      b.title='Saved articles';
      b.addEventListener('click',()=>{bookmarkMode=true; active='bookmarks'; localStorage.setItem('underreported-active-tab','bookmarks'); renderBookmarks(); updateBookmarkTab();});
      tabs.appendChild(b);
    }
    b.textContent=`🔖 Bookmarks${bookmarked.size?` (${bookmarked.size})`:''}`;
    b.classList.toggle('active',bookmarkMode);
  }

  function updateBookmarkTab(){
    const b=document.getElementById('bookmarks-tab');
    if(b){b.textContent=`🔖 Bookmarks${bookmarked.size?` (${bookmarked.size})`:''}`;b.classList.toggle('active',bookmarkMode);}
  }

  function renderBookmarks(){
    const root=document.getElementById('news-feed');
    if(!root)return;
    const items=(typeof allItems!=='undefined'?allItems:[]).filter(x=>bookmarked.has(itemKey(x)));
    root.innerHTML='';
    const sec=document.createElement('section'); sec.className='section bookmark-section';
    const head=document.createElement('div'); head.className='section-header';
    head.innerHTML=`<h2>🔖 Bookmarks</h2><span class="count">${items.length} saved</span>`;
    sec.appendChild(head);
    const body=document.createElement('div'); body.className='section-body';
    if(!items.length){body.innerHTML='<div class="empty">No saved articles yet. Tap 🔖 on any article to save it.</div>';}
    items.forEach((item,i)=>{
      const ar=document.createElement('article'); ar.className='news-item';
      const title=itemTitle(item),link=itemLink(item),desc=item.querySelector('description')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'',source=item.querySelector('source')?.textContent||'';
      ar.dataset.bookmarkKey=itemKey(item);
      ar.innerHTML=`<div class="bookmark-row"><h3><a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${escapeHtml(title)}</a></h3><button type="button" class="bookmark-btn saved" aria-label="Remove bookmark" title="Remove bookmark">🔖</button></div>${desc?`<p class="description">${escapeHtml(desc)}</p>`:''}<div class="meta"><span>${escapeHtml(typeof formatDate==='function'?formatDate(date):date)}</span>${source?`<span class="source">${escapeHtml(source)}</span>`:''}</div>`;
      ar.querySelector('.bookmark-btn').addEventListener('click',()=>{bookmarked.delete(itemKey(item));saveBookmarks();updateBookmarkTab();renderBookmarks();});
      body.appendChild(ar);
    });
    sec.appendChild(body); root.appendChild(sec);
  }

  function addBookmarkButtons(){
    document.querySelectorAll('.news-item').forEach(card=>{
      if(card.classList.contains('bookmark-section'))return;
      if(card.querySelector('.bookmark-btn'))return;
      const titleLink=card.querySelector('h3 a');
      if(!titleLink)return;
      let key='';
      if(typeof allItems!=='undefined'){
        const title=(titleLink.textContent||'').replace(/^\d+\.\s*/,'').trim().toLowerCase();
        const item=allItems.find(x=>itemTitle(x).toLowerCase()===title);
        if(item)key=itemKey(item);
      }
      if(!key){key='l:'+(titleLink.href||'').toLowerCase().replace(/[?#].*$/,'').replace(/\/$/,'');}
      const btn=document.createElement('button');
      btn.type='button'; btn.className='bookmark-btn'+(bookmarked.has(key)?' saved':'');
      btn.textContent=bookmarked.has(key)?'🔖':'🔖';
      btn.setAttribute('aria-label',bookmarked.has(key)?'Remove bookmark':'Bookmark article');
      btn.title=bookmarked.has(key)?'Remove bookmark':'Bookmark article';
      btn.dataset.bookmarkKey=key;
      btn.addEventListener('click',e=>{
        e.preventDefault(); e.stopPropagation();
        if(bookmarked.has(key))bookmarked.delete(key);else bookmarked.add(key);
        saveBookmarks();
        btn.classList.toggle('saved',bookmarked.has(key));
        btn.setAttribute('aria-label',bookmarked.has(key)?'Remove bookmark':'Bookmark article');
        btn.title=bookmarked.has(key)?'Remove bookmark':'Bookmark article';
        updateBookmarkTab();
      });
      const h=card.querySelector('h3');
      h?.insertAdjacentElement('beforebegin',btn);
    });
    updateBookmarkTab();
  }

  // If the user selected Bookmarks, keep that view after a feed refresh.
  function keepBookmarkView(){
    if(bookmarkMode){renderBookmarks();}
    else addBookmarkButtons();
  }

  const observer=new MutationObserver(()=>{if(rendering)return;setTimeout(keepBookmarkView,0);});
  function start(){
    ensureBookmarkTab();
    if(typeof active!=='undefined' && active==='bookmarks')bookmarkMode=true;
    const root=document.getElementById('news-feed'); if(root)observer.observe(root,{childList:true,subtree:true});
    const tabs=document.getElementById('tabs'); if(tabs)new MutationObserver(()=>{ensureBookmarkTab();}).observe(tabs,{childList:true});
    setTimeout(()=>{ensureBookmarkTab();keepBookmarkView();},50);
    setInterval(()=>{ensureBookmarkTab();},1000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>'''

STYLE = r'''<style id="bookmarks-v1-style">
.bookmark-row{display:flex;align-items:flex-start;gap:8px}.bookmark-row h3{flex:1;margin:0}.bookmark-btn{border:0;background:transparent;padding:2px 4px;cursor:pointer;font-size:18px;line-height:1;opacity:.45;border-radius:6px}.bookmark-btn:hover,.bookmark-btn.saved{opacity:1}.bookmark-btn:focus-visible{outline:2px solid var(--accent,#2563eb);outline-offset:2px}.bookmark-section .bookmark-btn{opacity:1}.bookmark-section .news-item{position:relative}.bookmark-section .bookmark-row{padding-right:2px}@media(max-width:700px){.bookmark-btn{font-size:17px;padding:1px 3px}}
</style>'''

s=P.read_text(encoding='utf-8')
while MARKER in s:
    a=s.find(MARKER); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]
while '<style id="bookmarks-v1-style">' in s:
    a=s.find('<style id="bookmarks-v1-style">'); b=s.find('</style>',a)
    if b<0: break
    s=s[:a]+s[b+8:]
if '</head>' not in s: raise SystemExit('head not found')
s=s.replace('</head>',STYLE+'\n</head>',1)
if '</body>' not in s: raise SystemExit('body not found')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed persistent article bookmarks and Bookmarks tab.')
