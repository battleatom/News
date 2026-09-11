#!/usr/bin/env python3
from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')

STYLE_ID = 'underreported-age-border-v1'
SCRIPT_ID = 'underreported-age-border-js-v1'

for marker, end_tag in [(f'<style id="{STYLE_ID}">', '</style>'), (f'<script id="{SCRIPT_ID}">', '</script>')]:
    while marker in text:
        start = text.find(marker)
        end = text.find(end_tag, start)
        if end < 0:
            break
        text = text[:start] + text[end + len(end_tag):]

style = f'''<style id="{STYLE_ID}">
.news-item.underreported-item.age-blue{{border-left:5px solid #2563eb!important}}
.news-item.underreported-item.age-green{{border-left:5px solid #16a34a!important}}
.news-item.underreported-item.age-orange{{border-left:5px solid #f97316!important}}
.news-item.underreported-item.age-purple{{border-left:5px solid #9333ea!important}}
.news-item.underreported-item.age-red{{border-left:5px solid #dc2626!important}}
.underreported-age-key{{display:flex;flex-wrap:wrap;gap:8px 12px;margin:6px 0 12px;font-size:11px;opacity:.82}}
.underreported-age-key span{{display:inline-flex;align-items:center;gap:5px}}
.underreported-age-key i{{display:inline-block;width:9px;height:9px;border-radius:2px}}
.underreported-age-key .b{{background:#2563eb}}.underreported-age-key .g{{background:#16a34a}}.underreported-age-key .o{{background:#f97316}}.underreported-age-key .p{{background:#9333ea}}.underreported-age-key .r{{background:#dc2626}}
</style>'''

script = f'''<script id="{SCRIPT_ID}">
(function(){{
  'use strict';
  function decorate(){{
    if((typeof active!=='undefined'&&active!=='underreported')&&document.body?.dataset?.activeTab!=='underreported')return;
    const cards=[...document.querySelectorAll('.underreported-item')];
    cards.forEach(card=>{{
      card.classList.remove('age-blue','age-green','age-orange','age-purple','age-red');
      const metaDate=card.querySelector('.meta span:first-child')?.textContent?.trim()||'';
      const dt=new Date(metaDate);
      if(Number.isNaN(dt.getTime()))return;
      const age=(Date.now()-dt.getTime())/86400000;
      let cls='age-red';
      if(age<=2)cls='age-blue';
      else if(age<=4)cls='age-green';
      else if(age<=7)cls='age-orange';
      else if(age<=10)cls='age-purple';
      card.classList.add(cls);
    }});
    const section=document.querySelector('#news-feed .section');
    if(section&&!section.querySelector('.underreported-age-key')){{
      const key=document.createElement('div');
      key.className='underreported-age-key';
      key.innerHTML='<span><i class="b"></i>0–2 days</span><span><i class="g"></i>2–4 days</span><span><i class="o"></i>4–7 days</span><span><i class="p"></i>7–10 days</span><span><i class="r"></i>10–14 days</span>';
      const body=section.querySelector('.section-body');
      if(body)section.insertBefore(key,body);
    }}
  }}
  const obs=new MutationObserver(()=>requestAnimationFrame(decorate));
  function start(){{
    decorate();
    const feed=document.getElementById('news-feed');
    if(feed)obs.observe(feed,{{childList:true,subtree:true}});
    document.addEventListener('click',e=>{{if(e.target.closest('.tab'))requestAnimationFrame(decorate)}});
  }}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{{once:true}});else start();
}})();
</script>'''

text = text.replace('</head>', style + '</head>', 1)
text = text.replace('</body>', script + '</body>', 1)
path.write_text(text, encoding='utf-8')
print('Added Underreported age-border legend and card coloring.')
