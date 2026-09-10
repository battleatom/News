from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Audio: Web Audio on mobile is most reliable when the AudioContext is created,
# the tone is scheduled, and resume() is requested from the user's tap path.
old_audio_guard = "if(!audioContext||audioContext.state!=='running')return false;"
new_audio_guard = "if(!audioContext)return false;"
if old_audio_guard not in s:
    raise SystemExit('Expected V2.2 synthPop guard not found')
s = s.replace(old_audio_guard, new_audio_guard, 1)

old_enable = """  async function enableSound(test){
    const ok=await ensureAudio();
    if(ok){try{localStorage.setItem(SOUND_KEY,'on')}catch(e){};if(test)synthPop();}
    renderStatus();return ok;
  }"""
new_enable = """  async function enableSound(test){
    let ok=false;
    try{
      if(!audioContext)audioContext=new (window.AudioContext||window.webkitAudioContext)();
      // Schedule the confirmation tone while still in the direct tap/click path.
      // Suspended AudioContexts keep currentTime paused, so the scheduled tone
      // begins when resume() succeeds instead of being lost after an await.
      if(test)synthPop();
      if(audioContext.state==='suspended')await audioContext.resume();
      audioReady=audioContext.state==='running';
      ok=audioReady;
    }catch(e){audioReady=false;ok=false}
    if(ok){
      try{localStorage.setItem(SOUND_KEY,'on')}catch(e){}
      if(test)window.__lastSoundTestAt=Date.now();
    }
    renderStatus();return ok;
  }"""
if old_enable not in s:
    raise SystemExit('Expected V2.2 enableSound implementation not found')
s = s.replace(old_enable, new_enable, 1)

# Load More: preserve a real story's viewport position instead of an absolute
# document scroll coordinate. canonicalRender destroys/recreates the feed, so
# scrollY alone can still jump when layout above/inside the feed changes.
old_load = """  button.onclick=()=>{
    const scrollY=window.scrollY;
    loadCounts[active]=next;
    canonicalRender(allItems);
    requestAnimationFrame(()=>window.scrollTo({top:scrollY,behavior:'auto'}));
  };"""
new_load = """  button.onclick=()=>{
    const scrollY=window.scrollY;
    const oldCards=[...document.querySelectorAll('#news-feed .news-item')];
    const anchor=oldCards[oldCards.length-1]||null;
    const anchorHref=anchor?.querySelector('h3 a[href]')?.href||'';
    const anchorTop=anchor?.getBoundingClientRect().top??null;
    loadCounts[active]=next;
    canonicalRender(allItems);
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(anchorHref&&anchorTop!==null){
        const replacement=[...document.querySelectorAll('#news-feed .news-item h3 a[href]')]
          .find(a=>a.href===anchorHref)?.closest('.news-item');
        if(replacement){
          const delta=replacement.getBoundingClientRect().top-anchorTop;
          window.scrollBy({top:delta,left:0,behavior:'auto'});
          return;
        }
      }
      window.scrollTo({top:scrollY,behavior:'auto'});
    }));
  };"""
if old_load not in s:
    raise SystemExit('Expected Load More click implementation not found')
s = s.replace(old_load, new_load, 1)

P.write_text(s, encoding='utf-8')
print('Applied interaction hotfix: mobile-safe audio test tone and story-anchored Load More viewport.')
