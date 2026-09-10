from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')

STYLE='''<style id="related-coverage-v1-style">.related-coverage{margin:11px 0 0;padding:10px 0 0;border-top:1px solid var(--ui-line);font-size:10px;color:#64748b}.related-coverage strong{display:inline-block;color:#475569;margin-bottom:3px}.related-coverage a{display:block;margin-top:5px;color:#475569;text-decoration:none;font-weight:650}.related-coverage a:hover{text-decoration:underline}.related-coverage .source{color:#94a3b8;font-weight:500}</style>'''
SCRIPT=r'''<script id="related-coverage-v1">
(function(){
  'use strict';
  let queued=false;
  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
  function decorate(){
    document.querySelectorAll('#news-feed .news-item').forEach(card=>{
      if(card.querySelector('.related-coverage'))return;
      const titleEl=card.querySelector('h3 a');if(!titleEl)return;
      const title=titleEl.textContent.replace(/^\d+\.\s*/,'').trim();
      const item=(window.allItems||[]).find(x=>(x.querySelector('title')?.textContent||'').trim()===title);if(!item)return;
      const related=[...item.querySelectorAll('relatedArticles article')];if(!related.length)return;
      const box=document.createElement('div');box.className='related-coverage';box.dataset.sourceCount=String(related.length+1);
      box.innerHTML=`<strong>Coverage · ${related.length+1} sources</strong>`+related.slice(0,4).map(r=>{const t=r.querySelector('title')?.textContent||'';const l=r.querySelector('link')?.textContent||'#';const src=r.querySelector('source')?.textContent||'';return `<a href="${esc(l)}" target="_blank" rel="noopener noreferrer">${esc(t)}${src?' <span class="source">— '+esc(src)+'</span>':''}</a>`}).join('');
      card.appendChild(box);
    });
  }
  function queueDecorate(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;decorate();});}
  function start(){const root=document.getElementById('news-feed');if(root)new MutationObserver(queueDecorate).observe(root,{childList:true,subtree:true});decorate();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
</script>'''

for marker,tag,close in (("related-coverage-v1",'<script id="related-coverage-v1">','</script>'),("related-coverage-v1-style",'<style id="related-coverage-v1-style">','</style>')):
    while tag in s:
        a=s.find(tag);b=s.find(close,a)
        if b<0:break
        s=s[:a]+s[b+len(close):]
if '</head>' not in s:raise SystemExit('Missing </head>')
s=s.replace('</head>',STYLE+'\n</head>',1)
if '</body>' not in s:raise SystemExit('Missing </body>')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed event-driven related coverage with source-count context.')
