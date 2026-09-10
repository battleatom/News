from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')
marker = '<script id="new-badge-expiry-v1">'
while marker in s:
    a = s.find(marker)
    b = s.find('</script>', a)
    if b < 0:
        break
    s = s[:a] + s[b + 9:]

# Keep every notification-audio state value on window. Global lexical `let`
# bindings can create a temporal-dead-zone across generated script blocks when a
# browser interaction fires while later blocks are still initializing.
state = """window.__audioContext=window.__audioContext||null;
window.__audioUnlocked=Boolean(window.__audioUnlocked);
window.__newArticleAudio=window.__newArticleAudio||null;
window.__newArticleAudioPrimed=Boolean(window.__newArticleAudioPrimed);"""
for old_state in (
    "let audioContext=null,audioUnlocked=false;\nwindow.__newArticleAudio=window.__newArticleAudio||null;\nwindow.__newArticleAudioPrimed=Boolean(window.__newArticleAudioPrimed);",
    "let audioContext=null,audioUnlocked=false,newArticleAudio=null,audioPrimed=false;",
    "let audioContext=null,audioUnlocked=false;",
):
    if old_state in s:
        s = s.replace(old_state, state, 1)
        break

new_audio = """function ensureNewArticleAudio(){let audio=window.__newArticleAudio;if(!audio){audio=new Audio('assets/new-article-pop.mp3');audio.preload='auto';audio.volume=0.85;audio.setAttribute('playsinline','');window.__newArticleAudio=audio;}return audio;}
async function unlockPopAudio(){let mediaUnlocked=false;try{const audio=ensureNewArticleAudio();if(!window.__newArticleAudioPrimed){const previousMuted=audio.muted,previousVolume=audio.volume;audio.muted=true;audio.volume=0;audio.currentTime=0;const started=audio.play();if(started&&typeof started.then==='function')await started;audio.pause();audio.currentTime=0;audio.muted=previousMuted;audio.volume=previousVolume||0.85;window.__newArticleAudioPrimed=true;}mediaUnlocked=true;}catch(e){console.info('MP3 notification audio could not be primed yet.',e);}try{if(!window.__audioContext)window.__audioContext=new (window.AudioContext||window.webkitAudioContext)();if(window.__audioContext.state==='suspended')await window.__audioContext.resume();window.__audioUnlocked=mediaUnlocked||window.__audioContext.state==='running';}catch(e){window.__audioUnlocked=mediaUnlocked;}return window.__audioUnlocked;}
function playSynthNewArticlePop(){const ctx=window.__audioContext;if(!ctx||ctx.state!=='running')return;try{const now=ctx.currentTime;const osc=ctx.createOscillator(),gain=ctx.createGain();osc.type='sine';osc.frequency.setValueAtTime(620,now);osc.frequency.exponentialRampToValueAtTime(1080,now+0.055);gain.gain.setValueAtTime(0.0001,now);gain.gain.exponentialRampToValueAtTime(0.16,now+0.008);gain.gain.exponentialRampToValueAtTime(0.0001,now+0.085);osc.connect(gain);gain.connect(ctx.destination);osc.start(now);osc.stop(now+0.09);}catch(e){}}
function playNewArticlePop(){if(!window.__audioUnlocked)return;try{const audio=ensureNewArticleAudio();audio.muted=false;audio.volume=0.85;audio.pause();audio.currentTime=0;const started=audio.play();if(started&&typeof started.catch==='function')started.catch(()=>playSynthNewArticlePop());}catch(e){playSynthNewArticlePop();}}
function primeNewArticleAudio(){if(window.__newArticleAudioPrimed&&window.__audioUnlocked)return;void unlockPopAudio();}
document.addEventListener('pointerdown',primeNewArticleAudio,{capture:true,passive:true});document.addEventListener('keydown',primeNewArticleAudio,{capture:true});"""

# Replace the currently generated MP3 implementation when present.
media_pattern = re.compile(
    r"function ensureNewArticleAudio\(\)\{.*?document\.addEventListener\('keydown',primeNewArticleAudio,\{capture:true\}\);",
    re.S,
)
if media_pattern.search(s):
    s = media_pattern.sub(new_audio, s, count=1)
else:
    # Upgrade the older synthesized-only implementation on a clean/base page.
    old_audio = """function unlockPopAudio(){try{if(!audioContext)audioContext=new (window.AudioContext||window.webkitAudioContext)();if(audioContext.state==='suspended')audioContext.resume();audioUnlocked=true;}catch(e){audioUnlocked=false;}}
function playNewArticlePop(){if(!audioUnlocked||!audioContext)return;try{const now=audioContext.currentTime;const osc=audioContext.createOscillator(),gain=audioContext.createGain();osc.type='sine';osc.frequency.setValueAtTime(620,now);osc.frequency.exponentialRampToValueAtTime(1080,now+0.055);gain.gain.setValueAtTime(0.0001,now);gain.gain.exponentialRampToValueAtTime(0.16,now+0.008);gain.gain.exponentialRampToValueAtTime(0.0001,now+0.085);osc.connect(gain);gain.connect(audioContext.destination);osc.start(now);osc.stop(now+0.09);}catch(e){}}"""
    if old_audio in s:
        s = s.replace(old_audio, new_audio, 1)
    elif 'assets/new-article-pop.mp3' not in s:
        raise SystemExit('Could not install uploaded new-article audio')

if re.search(r'\blet\s+audioContext\b|\blet\s+audioUnlocked\b', s):
    raise SystemExit('Lexical notification-audio state remains in generated page')

script = r'''<script id="new-badge-expiry-v1">
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
s = s.replace('</body>', script + '\n</body>', 1)
p.write_text(s, encoding='utf-8')
print('NEW badges expire after one hour and all notification audio state uses stable window storage.')
