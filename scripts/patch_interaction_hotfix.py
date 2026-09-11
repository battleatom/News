from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Compatibility cleanup only. Infinite scrolling now lives in patch_load_more.py
# and the status/NEW controllers no longer generate an audio path.
s = s.replace('if(newCount>0)playNewArticlePop();', '')
s = s.replace("if(newCount>0&&typeof window.__queueNewArticlePopV23==='function')window.__queueNewArticlePopV23(newCount);", '')
s = s.replace('if(manual)unlockPopAudio();', '')
s = s.replace('let audioContext=null,audioUnlocked=false;\n', '')

# Older site-features builds placed both Web Audio helpers directly before
# normalizeDuplicateKey(). Remove that entire helper block by its stable boundary
# rather than trying to balance nested JavaScript braces with a regex.
s, removed_audio = re.subn(
    r'function unlockPopAudio\(\)\{.*?\nfunction normalizeDuplicateKey',
    'function normalizeDuplicateKey',
    s,
    count=1,
    flags=re.S,
)
if not removed_audio and ('AudioContext' in s or 'playNewArticlePop' in s):
    raise SystemExit('Retired Web Audio block is still present but could not be removed safely')

# Browser refresh dedupe must mirror the server rule: duplicates are collapsed
# within a category, not across unrelated tabs. X is a fixed-slot product surface,
# so each xTopic is its own identity even if a lead article also appears elsewhere.
old_dedupe = "function dedupeFetchedItems(items){const seen=new Set(),out=[];for(const item of items){const key=normalizeDuplicateKey(item);if(seen.has(key))continue;seen.add(key);out.push(item);}return {items:out,removed:items.length-out.length};}"
new_dedupe = "function dedupeFetchedItems(items){const seen=new Set(),out=[];for(const item of items){const category=(item.querySelector('category')?.textContent||'world').trim().toLowerCase();const topic=(item.querySelector('xTopic')?.textContent||'').trim().toLowerCase();const identity=category==='x'&&topic?'x-topic:'+topic:category+'|'+normalizeDuplicateKey(item);if(seen.has(identity))continue;seen.add(identity);out.push(item);}return {items:out,removed:items.length-out.length};}"
if old_dedupe in s:
    s=s.replace(old_dedupe,new_dedupe,1)
elif new_dedupe not in s:
    raise SystemExit('Could not locate browser duplicate filter for category-aware hardening')

# Guard against stale generated fragments from older builds. These should be no-ops
# on a clean build, but keeping the cleanup idempotent prevents old generated HTML
# from resurrecting retired controls.
s = s.replace(
    '<button id="sound-alerts-toggle" type="button" data-enabled="${soundEnabled()?\'true\':\'false\'}">${soundEnabled()?\'🔊 Alerts on\':\'🔔 Enable sound\'}</button>',
    '',
)
s = s.replace(
    "    const sound=byId('sound-alerts-toggle');if(sound)sound.onclick=()=>{void enableSound(true)};\n",
    '',
)

# Sticky positioning is defeated when an ancestor establishes a clipping scroll
# container. Desktop already behaves correctly; on mobile let the main container
# remain visible while clipping only page-level horizontal overflow. This keeps the
# utility bar at the viewport top and the category rail directly below it.
marker = '<style id="mobile-sticky-nav-v1">'
while marker in s:
    start=s.find(marker); end=s.find('</style>',start)
    if end < 0: break
    s=s[:start]+s[end+8:]
sticky = '''<style id="mobile-sticky-nav-v1">
@media(max-width:760px){
  html,body{overflow-x:clip!important}
  html body .container{overflow:visible!important}
  html body .toolbar{position:sticky!important;top:0!important;z-index:100!important}
  html body .tabs{position:sticky!important;top:34px!important;z-index:99!important}
}
</style>'''
s=s.replace('</head>',sticky+'\n</head>',1)

P.write_text(s, encoding='utf-8')
print('Applied final interaction cleanup, category-aware browser dedupe, and mobile sticky navigation fix.')
