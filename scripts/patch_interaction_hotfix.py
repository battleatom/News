from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Remove the visible alert control entirely. Also disable the browser audio path
# so a previously saved localStorage preference cannot keep making sounds after
# the control is gone.
s = s.replace(
    '<button id="sound-alerts-toggle" type="button" data-enabled="${soundEnabled()?\'true\':\'false\'}">${soundEnabled()?\'🔊 Alerts on\':\'🔔 Enable sound\'}</button>',
    '',
    1,
)
s = s.replace(
    "    const sound=byId('sound-alerts-toggle');if(sound)sound.onclick=()=>{void enableSound(true)};\n",
    '',
    1,
)
s = s.replace(
    "  window.enableNewArticleSound=enableSound;\n  window.playNewArticlePop=function(){if(!soundEnabled())return false;if(audioReady&&synthPop())return true;void ensureAudio().then(ok=>{if(ok)synthPop()});return false};",
    "  window.enableNewArticleSound=async function(){return false};\n  window.playNewArticlePop=function(){return false};",
    1,
)
s = s.replace(
    "  function activateRememberedSound(){if(soundEnabled()&&!audioReady)void ensureAudio()}\n  document.addEventListener('pointerdown',activateRememberedSound,{capture:true,passive:true});\n  document.addEventListener('keydown',activateRememberedSound,{capture:true});\n",
    '',
    1,
)

# Replace button-driven pagination with automatic infinite scrolling. A sentinel
# near the bottom requests the next 10 stories. During the unavoidable full feed
# re-render, the last visible story is used as a viewport anchor so the user does
# not jump to the top.
old = """function appendLoadMoreControl(data){
  const root=document.getElementById('news-feed');
  if(!root)return;
  root.querySelectorAll('.load-more-wrap').forEach(el=>el.remove());
  if(data.available.length<=data.count)return;
  const more=document.createElement('div');
  more.className='load-more-wrap';
  const button=document.createElement('button');
  button.type='button';
  button.className='load-more';
  const next=Math.min(data.count+STORIES_PER_PAGE,data.available.length);
  button.textContent=`Load 10 more (${next} of ${data.available.length})`;
  button.onclick=()=>{
    const scrollY=window.scrollY;
    loadCounts[active]=next;
    canonicalRender(allItems);
    requestAnimationFrame(()=>window.scrollTo({top:scrollY,behavior:'auto'}));
  };
  more.appendChild(button);
  // Keep pagination outside the category section. Several category renderers
  // rebuild their section after canonicalRender and could otherwise delete it.
  root.appendChild(more);
}"""
new = """function appendLoadMoreControl(data){
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
}"""
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('Expected Load More or infinite-scroll implementation not found')

P.write_text(s, encoding='utf-8')
print('Removed alert button/audio path and ensured anchored infinite scrolling.')
