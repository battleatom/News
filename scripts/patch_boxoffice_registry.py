from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')
old = """  render=locationAwareRender;
  if(previousCanonicalRender){
    canonicalRender=function(items){
      if(active==='boxoffice') return locationAwareRender(items);
      return previousCanonicalRender(items);
    };
  }
"""
new = """  window.__categoryRenderers=window.__categoryRenderers||{};
  window.__categoryRenderers.boxoffice=locationAwareRender;
"""
if old not in s:
    # Idempotent builds may already contain the normalized registry form.
    if new in s:
        print('Box Office is already registered through the canonical category renderer registry.')
    else:
        raise SystemExit('Expected Box Office canonical wrapper was not found; refusing nondeterministic cleanup')
else:
    s = s.replace(old, new, 1)
    print('Registered Box Office through canonical category renderer registry; removed duplicate canonicalRender wrapper.')

marker = '<script id="boxoffice-progressive-v1">'
while marker in s:
    start = s.find(marker)
    end = s.find('</script>', start)
    if end < 0:
        raise SystemExit('Malformed Box Office progressive block')
    s = s[:start] + s[end + len('</script>'):]

progressive = r'''<script id="boxoffice-progressive-v1">
(function(){
  if(window.__boxOfficeProgressiveV1===true)return;
  window.__boxOfficeProgressiveV1=true;
  const INITIAL_PER_GROUP=5;
  const PAGE_PER_GROUP=3;
  let domObserver=null;
  let scrollObserver=null;

  function disconnectObservers(){
    if(domObserver){try{domObserver.disconnect()}catch(e){}domObserver=null;}
    if(scrollObserver){try{scrollObserver.disconnect()}catch(e){}scrollObserver=null;}
  }

  function setShown(el,shown){
    if(!el)return;
    if(shown){el.style.removeProperty('display');el.removeAttribute('aria-hidden');}
    else{el.style.setProperty('display','none','important');el.setAttribute('aria-hidden','true');}
  }

  function ensureStyles(){
    if(document.getElementById('boxoffice-progressive-style'))return;
    const style=document.createElement('style');
    style.id='boxoffice-progressive-style';
    style.textContent=`
      #news-feed .movie-card{content-visibility:auto;contain-intrinsic-size:320px}
      .boxoffice-progressive-more{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;margin:16px 0 18px;padding:10px 12px;border:1px solid var(--ui-line);border-radius:12px;background:rgba(248,250,252,.66)}
      .boxoffice-progressive-more button{appearance:none;border:1px solid rgba(148,163,184,.55);border-radius:999px;background:rgba(255,255,255,.88);padding:8px 13px;font:inherit;font-size:.78rem;font-weight:800;color:inherit;cursor:pointer}
      .boxoffice-progressive-more .boxoffice-progressive-status{font-size:.72rem;font-weight:750;color:#64748b}
      @media(prefers-color-scheme:dark){.boxoffice-progressive-more{background:rgba(15,23,42,.42)}.boxoffice-progressive-more button{background:rgba(30,41,59,.86);border-color:rgba(148,163,184,.35)}.boxoffice-progressive-more .boxoffice-progressive-status{color:#a7b0bd}}
    `;
    document.head.appendChild(style);
  }

  function setupProgressiveBoxOffice(){
    if(active!=='boxoffice')return false;
    const root=document.getElementById('news-feed');
    if(!root||root.dataset.boxofficeProgressiveReady==='1')return false;
    const cards=[...root.querySelectorAll('.movie-card')];
    if(!cards.length)return false;

    root.dataset.boxofficeProgressiveReady='1';
    ensureStyles();

    const current=cards.filter(card=>!card.querySelector('.movie-status.status-upcoming'));
    const upcoming=cards.filter(card=>card.querySelector('.movie-status.status-upcoming'));
    let currentShown=Math.min(INITIAL_PER_GROUP,current.length);
    let upcomingShown=Math.min(INITIAL_PER_GROUP,upcoming.length);

    const localTitle=root.querySelector('.boxoffice-section-title');
    const localNodes=[];
    if(localTitle){
      let node=localTitle;
      while(node){localNodes.push(node);node=node.nextElementSibling;}
    }

    const wrap=document.createElement('div');
    wrap.className='boxoffice-progressive-more';
    const button=document.createElement('button');
    button.type='button';
    const status=document.createElement('span');
    status.className='boxoffice-progressive-status';
    wrap.append(button,status);
    if(localTitle)localTitle.before(wrap);
    else{
      const body=root.querySelector('.section-body');
      if(body)body.appendChild(wrap);else root.appendChild(wrap);
    }

    let loading=false;
    function apply(){
      current.forEach((card,index)=>setShown(card,index<currentShown));
      upcoming.forEach((card,index)=>setShown(card,index<upcomingShown));
      const shown=currentShown+upcomingShown;
      const total=cards.length;
      const remaining=Math.max(0,total-shown);
      const count=root.querySelector('.section-header .count');
      if(count)count.textContent=`Showing ${shown} of ${total} movies`;
      localNodes.forEach(node=>setShown(node,remaining===0));
      if(remaining===0){
        if(scrollObserver){try{scrollObserver.disconnect()}catch(e){}scrollObserver=null;}
        wrap.remove();
        return;
      }
      button.textContent=`Show more movies · ${remaining} remaining`;
      status.textContent='More load automatically as you scroll';
    }

    function loadMore(){
      if(loading||active!=='boxoffice')return;
      loading=true;
      currentShown=Math.min(current.length,currentShown+PAGE_PER_GROUP);
      upcomingShown=Math.min(upcoming.length,upcomingShown+PAGE_PER_GROUP);
      apply();
      requestAnimationFrame(()=>{loading=false;});
    }

    button.addEventListener('click',loadMore);
    apply();

    if('IntersectionObserver' in window&&wrap.isConnected){
      scrollObserver=new IntersectionObserver(entries=>{
        if(entries.some(entry=>entry.isIntersecting))loadMore();
      },{root:null,rootMargin:'500px 0px 500px 0px',threshold:0.01});
      scrollObserver.observe(wrap);
    }
    return true;
  }

  function armForRender(){
    disconnectObservers();
    const root=document.getElementById('news-feed');
    if(!root)return;
    delete root.dataset.boxofficeProgressiveReady;
    if(setupProgressiveBoxOffice())return;
    domObserver=new MutationObserver(()=>{
      if(active!=='boxoffice'){disconnectObservers();return;}
      if(setupProgressiveBoxOffice()&&domObserver){domObserver.disconnect();domObserver=null;}
    });
    domObserver.observe(root,{childList:true,subtree:true});
    window.setTimeout(()=>{if(domObserver){domObserver.disconnect();domObserver=null;}},12000);
  }

  const registry=window.__categoryRenderers=window.__categoryRenderers||{};
  const baseBoxOfficeRenderer=registry.boxoffice;
  if(typeof baseBoxOfficeRenderer==='function'){
    registry.boxoffice=function(items){
      const root=document.getElementById('news-feed');
      if(root)delete root.dataset.boxofficeProgressiveReady;
      const out=baseBoxOfficeRenderer(items);
      armForRender();
      return out;
    };
  }
})();
</script>'''

if '</body>' in s:
    s = s.replace('</body>', progressive + '\n</body>', 1)
else:
    s += '\n' + progressive + '\n'

P.write_text(s, encoding='utf-8')
print('Box Office registry cleanup complete with progressive movie loading and one canonical pagination owner.')
