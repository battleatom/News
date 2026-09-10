from pathlib import Path

P = Path('index.html')
SCRIPT_ID = 'bookmarks-v1'
MARKER = f'<script id="{SCRIPT_ID}">'

SCRIPT = r'''<script id="bookmarks-v1">
(function(){
  'use strict';
  const STORAGE_KEY='news-bookmarks-v1';
  const DATA_KEY='news-bookmark-data-v1';
  let bookmarkMode=false;
  let bookmarked=new Set(loadBookmarks());
  let bookmarkData=loadBookmarkData();
  let rendering=false;
  let decorateQueued=false;

  function loadBookmarks(){try{const v=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(v)?v:[];}catch(e){return[];}}
  function saveBookmarks(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify([...bookmarked]));}catch(e){}}
  function loadBookmarkData(){try{const v=JSON.parse(localStorage.getItem(DATA_KEY)||'{}');return v&&typeof v==='object'?v:{};}catch(e){return{};}}
  function saveBookmarkData(){try{localStorage.setItem(DATA_KEY,JSON.stringify(bookmarkData));}catch(e){}}
  function itemKey(item){const link=(item?.querySelector?.('link')?.textContent||'').trim().toLowerCase().replace(/[?#].*$/,'').replace(/\/$/,'');if(link)return 'l:'+link;const title=(item?.querySelector?.('title')?.textContent||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();return 't:'+title;}
  function itemTitle(item){return (item?.querySelector?.('title')?.textContent||'Untitled').trim();}
  function itemLink(item){return (item?.querySelector?.('link')?.textContent||'#').trim();}
  function escapeHtml(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
  function readItem(item){return {key:itemKey(item),title:itemTitle(item),link:itemLink(item),description:item?.querySelector?.('description')?.textContent||'',date:item?.querySelector?.('pubDate')?.textContent||'',source:item?.querySelector?.('source')?.textContent||''};}
  function rememberItem(item){if(!item)return;const data=readItem(item);if(!data.key)return;bookmarkData[data.key]=data;saveBookmarkData();}

  function ensureBookmarkTab(){
    const tabs=document.getElementById('tabs');if(!tabs)return;
    let b=document.getElementById('bookmarks-tab');
    if(!b){
      b=document.createElement('button');b.id='bookmarks-tab';b.className='tab';b.type='button';b.title='Saved articles';
      b.addEventListener('click',()=>{bookmarkMode=true;active='bookmarks';localStorage.setItem('underreported-active-tab','bookmarks');renderBookmarks();updateBookmarkTab();});
      tabs.appendChild(b);
    }
    updateBookmarkTab();
  }
  function updateBookmarkTab(){const b=document.getElementById('bookmarks-tab');if(b){b.textContent=`🔖 Bookmarks${bookmarked.size?` (${bookmarked.size})`:''}`;b.classList.toggle('active',bookmarkMode);}}

  function renderBookmarks(){
    const root=document.getElementById('news-feed');if(!root||rendering)return;
    rendering=true;
    try{
      const current=(typeof allItems!=='undefined'?allItems:[]);
      current.forEach(x=>{if(bookmarked.has(itemKey(x)))rememberItem(x);});
      const currentByKey={};current.forEach(x=>{currentByKey[itemKey(x)]=x;});
      const items=[...bookmarked].map(k=>currentByKey[k]||bookmarkData[k]).filter(Boolean);
      root.innerHTML='';
      const sec=document.createElement('section');sec.className='section bookmark-section';
      const head=document.createElement('div');head.className='section-header';head.innerHTML=`<h2>🔖 Bookmarks</h2><span class="count">${items.length} saved</span>`;sec.appendChild(head);
      const body=document.createElement('div');body.className='section-body';
      if(!items.length)body.innerHTML='<div class="empty">No saved articles yet. Tap 🔖 on any article to save it.</div>';
      items.forEach((item,i)=>{
        const ar=document.createElement('article');ar.className='news-item';
        const stored=typeof item==='object'&&typeof item.querySelector!=='function';
        const title=stored?(item.title||'Untitled'):itemTitle(item),link=stored?(item.link||'#'):itemLink(item),desc=stored?(item.description||''):item.querySelector('description')?.textContent||'',date=stored?(item.date||''):item.querySelector('pubDate')?.textContent||'',source=stored?(item.source||''):item.querySelector('source')?.textContent||'',bk=stored?(item.key||''):itemKey(item);
        ar.dataset.bookmarkKey=bk;
        ar.innerHTML=`<div class="bookmark-row"><h3><a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${escapeHtml(title)}</a></h3><button type="button" class="bookmark-btn saved" aria-label="Remove bookmark" title="Remove bookmark">🔖</button></div>${desc?`<p class="description">${escapeHtml(desc)}</p>`:''}<div class="meta"><span>${escapeHtml(typeof formatDate==='function'?formatDate(date):date)}</span>${source?`<span class="source">${escapeHtml(source)}</span>`:''}</div>`;
        ar.querySelector('.bookmark-btn').addEventListener('click',()=>{bookmarked.delete(bk);delete bookmarkData[bk];saveBookmarks();saveBookmarkData();updateBookmarkTab();renderBookmarks();});
        body.appendChild(ar);
      });
      sec.appendChild(body);root.appendChild(sec);
    }finally{requestAnimationFrame(()=>{rendering=false;});}
  }

  function addBookmarkButtons(){
    document.querySelectorAll('#news-feed .news-item').forEach(card=>{
      if(card.closest('.bookmark-section')||card.querySelector('.bookmark-btn'))return;
      const titleLink=card.querySelector('h3 a');if(!titleLink)return;
      let key='';
      if(typeof allItems!=='undefined'){
        const title=(titleLink.textContent||'').replace(/^\d+\.\s*/,'').trim().toLowerCase();
        const item=allItems.find(x=>itemTitle(x).toLowerCase()===title);if(item)key=itemKey(item);
      }
      if(!key)key='l:'+(titleLink.href||'').toLowerCase().replace(/[?#].*$/,'').replace(/\/$/,'');
      const btn=document.createElement('button');btn.type='button';btn.className='bookmark-btn'+(bookmarked.has(key)?' saved':'');btn.textContent='🔖';btn.dataset.bookmarkKey=key;
      function sync(){const saved=bookmarked.has(key);btn.classList.toggle('saved',saved);btn.setAttribute('aria-label',saved?'Remove bookmark':'Bookmark article');btn.title=saved?'Remove bookmark':'Bookmark article';}
      sync();
      btn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();if(bookmarked.has(key)){bookmarked.delete(key);delete bookmarkData[key];}else{bookmarked.add(key);if(typeof allItems!=='undefined'){const item=allItems.find(x=>itemKey(x)===key);if(item)rememberItem(item);}}saveBookmarks();saveBookmarkData();sync();updateBookmarkTab();});
      const h=card.querySelector('h3');h?.insertAdjacentElement('beforebegin',btn);
    });
    updateBookmarkTab();
  }

  function keepBookmarkView(){if(bookmarkMode)renderBookmarks();else addBookmarkButtons();}
  function queueDecorate(){if(decorateQueued||rendering)return;decorateQueued=true;queueMicrotask(()=>{decorateQueued=false;keepBookmarkView();});}

  function start(){
    if(typeof allItems!=='undefined')allItems.forEach(x=>{if(bookmarked.has(itemKey(x)))rememberItem(x);});
    ensureBookmarkTab();if(typeof active!=='undefined'&&active==='bookmarks')bookmarkMode=true;
    const root=document.getElementById('news-feed');if(root)new MutationObserver(queueDecorate).observe(root,{childList:true,subtree:true});
    const tabs=document.getElementById('tabs');
    if(tabs){
      /* Capture phase clears bookmark mode before a destination tab's onclick renders. */
      tabs.addEventListener('click',e=>{const tab=e.target.closest('.tab');if(tab&&tab.id!=='bookmarks-tab'){bookmarkMode=false;updateBookmarkTab();}},true);
      new MutationObserver(()=>ensureBookmarkTab()).observe(tabs,{childList:true});
    }
    ensureBookmarkTab();keepBookmarkView();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
</script>'''

STYLE = r'''<style id="bookmarks-v1-style">
.bookmark-row{display:flex;align-items:flex-start;gap:8px}.bookmark-row h3{flex:1;margin:0}.bookmark-btn{border:0;background:transparent;padding:2px 4px;cursor:pointer;font-size:18px;line-height:1;opacity:.45;border-radius:6px}.bookmark-btn:hover,.bookmark-btn.saved{opacity:1}.bookmark-btn:focus-visible{outline:2px solid var(--accent,#2563eb);outline-offset:2px}.bookmark-section .bookmark-btn{opacity:1}.bookmark-section .news-item{position:relative}.bookmark-section .bookmark-row{padding-right:2px}@media(max-width:700px){.bookmark-btn{font-size:17px;padding:1px 3px}}
</style>'''

s=P.read_text(encoding='utf-8')
while MARKER in s:
    a=s.find(MARKER);b=s.find('</script>',a)
    if b<0:break
    s=s[:a]+s[b+9:]
while '<style id="bookmarks-v1-style">' in s:
    a=s.find('<style id="bookmarks-v1-style">');b=s.find('</style>',a)
    if b<0:break
    s=s[:a]+s[b+8:]
if '</head>' not in s:raise SystemExit('head not found')
s=s.replace('</head>',STYLE+'\n</head>',1)
if '</body>' not in s:raise SystemExit('body not found')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed event-driven persistent article bookmarks with pre-render tab state cleanup.')
