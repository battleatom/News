from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

start = s.find('<script id="site-features-v2">')
end = s.find('</script>', start) if start >= 0 else -1
if start >= 0 and end >= 0:
    block = s[start:end]
    block = re.sub(
        r"\nlet audioContext=null,audioUnlocked=false;\nfunction unlockPopAudio\(\).*?\nfunction normalizeDuplicateKey",
        "\nfunction normalizeDuplicateKey",
        block,
        count=1,
        flags=re.S,
    )
    block = block.replace('if(manual)unlockPopAudio();', '')
    block = block.replace(
        'if(newCount>0)playNewArticlePop();',
        "if(newCount>0&&typeof window.__queueNewArticlePopV23==='function')window.__queueNewArticlePopV23(newCount);",
    )
    s = s[:start] + block + s[end:]

for marker in ('new-article-audio-v1', 'new-article-audio-v2'):
    needle = f'<script id="{marker}">'
    while needle in s:
        a = s.find(needle)
        b = s.find('</script>', a)
        if b < 0:
            break
        s = s[:a] + s[b + len('</script>'):]

s = s.replace(
    "if(test&&audioReady)synthPop();renderStatus();return audioReady",
    "if(test&&audioReady&&typeof window.playNewArticlePop==='function')window.playNewArticlePop();renderStatus();return audioReady",
)
s = s.replace(
    'window.__alertsStatusV282=true;',
    'window.__alertsStatusV22=true;window.__alertsStatusV282=true;',
)

RESTORE = r'''<script id="deferred-active-tab-v282">
(function(){
  'use strict';
  const wanted=window.__pendingActiveTab||'top';
  if(!wanted||wanted==='top'){window.__deferredActiveTabV282=true;return;}
  let tries=0;
  const restore=()=>{
    tries++;
    const ready=Array.isArray(window.allItems)&&window.allItems.length>0;
    if(!ready){if(tries<100)setTimeout(restore,50);return;}
    const selector=`#tabs > .tab[data-nav-key="${CSS.escape(wanted)}"]`;
    const button=document.querySelector(selector);
    if(!button){if(tries<100)setTimeout(restore,50);return;}
    // Exercise the same handler a user click uses. This keeps all special renderers,
    // bookmark state, location logic and persisted tab state in sync.
    button.click();
  };
  setTimeout(restore,0);
  window.__deferredActiveTabV282=true;
})();
</script>'''
if 'id="deferred-active-tab-v282"' in s:
    a=s.find('<script id="deferred-active-tab-v282">')
    b=s.find('</script>',a)
    if b>=0:s=s[:a]+s[b+9:]
s = s.replace('</body>', RESTORE + '\n</body>', 1)

if s.count('id="alerts-status-v22"') != 1:
    raise SystemExit('Expected exactly one alerts-status-v22 controller')
if s.count('window.playNewArticlePop=function') != 1:
    raise SystemExit('Expected exactly one authoritative window.playNewArticlePop implementation')
if 'window.__loadMoreRevealOnlyV282=true' not in s:
    raise SystemExit('Reveal-only pagination is missing from final runtime')
if 'let audioContext=null,audioUnlocked=false;' in s:
    raise SystemExit('Legacy site-features audio engine still present')
if "window.playNewArticlePop();renderStatus();return audioReady" not in s:
    raise SystemExit('Sound enable confirmation is not using the public alert path')
if 'button.click();' not in s:
    raise SystemExit('Deferred active-tab restore is not using canonical tab click path')

P.write_text(s, encoding='utf-8')
print('V2.8.2 runtime cleanup complete: single audio owner, unified alert path, reveal-only pagination, and canonical deferred tab restore verified.')
