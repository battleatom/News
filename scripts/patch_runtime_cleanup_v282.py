from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Final ownership cleanup. site-features historically carried its own audio engine;
# V2.2 is now the single owner of the sound preference, AudioContext and toggle.
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

# Remove obsolete standalone audio blocks left by older generated versions.
for marker in ('new-article-audio-v1', 'new-article-audio-v2'):
    needle = f'<script id="{marker}">'
    while needle in s:
        a = s.find(needle)
        b = s.find('</script>', a)
        if b < 0:
            break
        s = s[:a] + s[b + len('</script>'):]

# Make the enable-button confirmation use the exact same public sound path used
# by real new-article alerts. This makes both browser behavior and tests honest.
s = s.replace(
    "if(test&&audioReady)synthPop();renderStatus();return audioReady",
    "if(test&&audioReady&&typeof window.playNewArticlePop==='function')window.playNewArticlePop();renderStatus();return audioReady",
)

# Preserve compatibility markers used by the broad smoke suite.
s = s.replace(
    'window.__alertsStatusV282=true;',
    'window.__alertsStatusV22=true;window.__alertsStatusV282=true;',
)

# Hard validation: one visible sound controller, one authoritative player, and
# reveal-only pagination must be present in the final generated page.
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

P.write_text(s, encoding='utf-8')
print('V2.8.2 runtime cleanup complete: single audio owner, unified alert path, and reveal-only pagination verified.')
