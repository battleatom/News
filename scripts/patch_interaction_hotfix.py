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
s = re.sub(
    r'function unlockPopAudio\(\)\{.*?\}\nfunction playNewArticlePop\(\)\{.*?\}\n',
    '',
    s,
    count=1,
    flags=re.S,
)

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

P.write_text(s, encoding='utf-8')
print('Applied final interaction cleanup; retired Web Audio code removed from generated page.')
