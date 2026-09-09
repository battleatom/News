from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
marker='<script id="new-badge-expiry-v1">'
while marker in s:
    a=s.find(marker); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]

old_state="let audioContext=null,audioUnlocked=false;"
new_state="let audioContext=null,audioUnlocked=false,newArticleAudio=null,audioPrimed=false;"
if old_state in s:
    s=s.replace(old_state,new_state,1)

old_audio="""function unlockPopAudio(){try{if(!audioContext)audioContext=new (window.AudioContext||window.webkitAudioContext)();if(audioContext.state==='suspended')audioContext.resume();audioUnlocked=true;}catch(e){audioUnlocked=false;}}\nfunction playNewArticlePop(){if(!audioUnlocked||!audioContext)return;try{const now=audioContext.currentTime;const osc=audioContext.createOscillator(),gain=audioContext.createGain();osc.type='sine';osc.frequency.setValueAtTime(620,now);osc.frequency.exponentialRampToValueAtTime(1080,now+0.055);gain.gain.setValueAtTime(0.0001,now);gain.gain.exponentialRampToValueAtTime(0.16,now+0.008);gain.gain.exponentialRampToValueAtTime(0.0001,now+0.085);osc.connect(gain);gain.connect(audioContext.destination);osc.start(now);osc.stop(now+0.09);}catch(e){}}"""
new_audio="""function ensureNewArticleAudio(){if(!newArticleAudio){newArticleAudio=new Audio('assets/new-article-pop.mp3');newArticleAudio.preload='auto';newArticleAudio.volume=0.85;newArticleAudio.setAttribute('playsinline','');}return newArticleAudio;}\nasync function unlockPopAudio(){let mediaUnlocked=false;try{const audio=ensureNewArticleAudio();if(!audioPrimed){const previousMuted=audio.muted,previousVolume=audio.volume;audio.muted=true;audio.volume=0;audio.currentTime=0;const started=audio.play();if(started&&typeof started.then==='function')await started;audio.pause();audio.currentTime=0;audio.muted=previousMuted;audio.volume=previousVolume||0.85;audioPrimed=true;}mediaUnlocked=true;}catch(e){console.info('MP3 notification audio could not be primed yet.',e);}try{if(!audioContext)audioContext=new (window.AudioContext||window.webkitAudioContext)();if(audioContext.state==='suspended')await audioContext.resume();audioUnlocked=mediaUnlocked||audioContext.state==='running';}catch(e){audioUnlocked=mediaUnlocked;}return audioUnlocked;}\nfunction playSynthNewArticlePop(){if(!audioContext||audioContext.state!=='running')return;try{const now=audioContext.currentTime;const osc=audioContext.createOscillator(),gain=audioContext.createGain();osc.type='sine';osc.frequency.setValueAtTime(620,now);osc.frequency.exponentialRampToValueAtTime(1080,now+0.055);gain.gain.setValueAtTime(0.0001,now);gain.gain.exponentialRampToValueAtTime(0.16,now+0.008);gain.gain.exponentialRampToValueAtTime(0.0001,now+0.085);osc.connect(gain);gain.connect(audioContext.destination);osc.start(now);osc.stop(now+0.09);}catch(e){}}\nfunction playNewArticlePop(){if(!audioUnlocked)return;try{const audio=ensureNewArticleAudio();audio.muted=false;audio.volume=0.85;audio.pause();audio.currentTime=0;const started=audio.play();if(started&&typeof started.catch==='function')started.catch(()=>playSynthNewArticlePop());}catch(e){playSynthNewArticlePop();}}\nfunction primeNewArticleAudio(){if(audioPrimed&&audioUnlocked)return;void unlockPopAudio();}\ndocument.addEventListener('pointerdown',primeNewArticleAudio,{capture:true,passive:true});document.addEventListener('keydown',primeNewArticleAudio,{capture:true});"""
if old_audio in s:
    s=s.replace(old_audio,new_audio,1)
elif "assets/new-article-pop.mp3" not in s:
    raise SystemExit('Could not install uploaded new-article audio')

script=r'''<script id="new-badge-expiry-v1">
function decorateNewBadges(){
 document.querySelectorAll('.news-item').forEach(card=>{
   const existing=card.querySelector('.new-badge');
   const meta=card.querySelector('.meta span');
   const fresh=meta&&isFresh(meta.textContent);
   if(existing&&!fresh) existing.remove();
   if(!existing&&fresh){const h=card.querySelector('h3');if(h){const badge=document.createElement('span');badge.className='new-badge';badge.textContent='NEW';h.appendChild(badge);}}
 });
}
setInterval(()=>{if(typeof decorateNewBadges==='function')decorateNewBadges();},60*1000);
</script>'''
s=s.replace('</body>',script+'\n</body>',1)
p.write_text(s,encoding='utf-8')
print('NEW badges expire after one hour and uploaded bubble-pop is primed by user interaction for reliable later refresh alerts.')
