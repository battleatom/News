from pathlib import Path

P = Path('index.html')
MARKER = 'top-cycle-reliability-v1'

s = P.read_text(encoding='utf-8')

# Remove an older generated copy so this patch stays idempotent.
while f'<script id="{MARKER}">' in s:
    a = s.find(f'<script id="{MARKER}">')
    b = s.find('</script>', a)
    if b < 0:
        break
    s = s[:a] + s[b + 9:]

if 'id="load-more-v1"' not in s:
    raise SystemExit('Load More / Top discovery script must be installed first')
if 'function topItemsNewestFirst' not in s or 'function readTopSeen' not in s:
    raise SystemExit('Top discovery helpers are missing')

SCRIPT = r'''<script id="top-cycle-reliability-v1">
(function(){
  'use strict';

  function currentTab(){
    try{return window.active || (typeof active!=='undefined'?active:'top')}catch(e){return window.active||'top'}
  }
  function currentItems(){
    try{return window.allItems || (typeof allItems!=='undefined'?allItems:[])}catch(e){return window.allItems||[]}
  }
  function nextCircularBatch(ordered){
    if(!ordered.length)return [];
    const keys=ordered.map(topStoryKey);
    const current=(window.topRotationKeys||[]).filter(k=>keys.includes(k));
    let start=0;
    if(current.length){
      const last=keys.indexOf(current[current.length-1]);
      if(last>=0)start=(last+1)%ordered.length;
    }else if(ordered.length>STORIES_PER_PAGE){
      // If navigation/re-rendering lost the explicit rotation state while the
      // daily seen set is already exhausted, move away from the newest batch
      // instead of re-rendering the same ten and appearing to do nothing.
      start=STORIES_PER_PAGE%ordered.length;
    }
    const circular=ordered.slice(start).concat(ordered.slice(0,start));
    return circular.slice(0,Math.min(STORIES_PER_PAGE,ordered.length));
  }

  window.cycleTopStoriesAndRefresh=async function(){
    if(currentTab()!=='top')return false;
    const items=currentItems();
    const ordered=topItemsNewestFirst(items);
    if(!ordered.length)return false;

    const seen=readTopSeen();
    const unseen=ordered.filter(item=>!seen.has(topStoryKey(item)));
    const wrapped=unseen.length===0;
    const batch=wrapped?nextCircularBatch(ordered):unseen.slice(0,STORIES_PER_PAGE);
    if(!batch.length)return false;

    window.topRotationKeys=batch.map(topStoryKey);
    loadCounts.top=STORIES_PER_PAGE;
    canonicalRender(items);

    const status=document.getElementById('status');
    if(status){
      status.textContent=wrapped
        ? `Continuing Top Stories cycle · ${batch.length} stories · checking for updates…`
        : `Showing ${batch.length} unseen Top Stories · checking for updates…`;
    }

    // Passive refresh: start it after the visible batch changes, but do not
    // make the discovery button wait for the network request. The canonical
    // refresh keeps all tabs current and preserves the active Top rotation.
    const refreshFn=window.refreshNewsFromPage || (typeof refreshNewsFromPage==='function'?refreshNewsFromPage:null);
    if(refreshFn){
      Promise.resolve(refreshFn(false)).catch(e=>console.error('Passive full-feed refresh failed:',e));
    }
    return true;
  };

  // Capture-phase delegation makes the button reliable after any tab rebuild.
  // It intentionally supersedes older per-button listeners without stacking
  // multiple Top cycles on a single click.
  document.addEventListener('click',async function(e){
    const btn=e.target?.closest?.('#refresh');
    if(!btn || currentTab()!=='top')return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if(btn.dataset.topCycleBusy==='1')return;
    btn.dataset.topCycleBusy='1';
    btn.disabled=true;
    btn.textContent='⟳ Checking…';
    try{
      await window.cycleTopStoriesAndRefresh();
    }catch(err){
      console.error('Top Stories cycle failed:',err);
    }finally{
      btn.dataset.topCycleBusy='';
      btn.disabled=false;
      btn.textContent='↻ Next Top Stories';
      if(typeof window.refreshPullStatsUI==='function')window.refreshPullStatsUI(false,'');
    }
  },true);
})();
</script>'''

if '</body>' not in s:
    raise SystemExit('Missing </body>')
s = s.replace('</body>', SCRIPT + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Made Top Stories truly revolving and hardened the discovery button across tab navigation.')
