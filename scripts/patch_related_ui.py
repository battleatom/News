from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')

STYLE='''<style id="related-coverage-v1-style">.related-coverage{margin:9px 0 0;padding:8px 10px;border-top:1px solid var(--ui-line);font-size:10px;color:#64748b}.related-coverage strong{color:#475569}.related-coverage a{display:block;margin-top:4px;color:#475569;text-decoration:underline}.related-coverage .source{color:#94a3b8}</style>'''
SCRIPT=r'''<script id="related-coverage-v1">
(function(){
  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
  function decorate(){
    document.querySelectorAll('.news-item').forEach(card=>{
      if(card.querySelector('.related-coverage'))return;
      const titleEl=card.querySelector('h3 a'); if(!titleEl)return;
      const title=titleEl.textContent.replace(/^\d+\.\s*/,'').trim();
      const item=(window.allItems||[]).find(x=>(x.querySelector('title')?.textContent||'').trim()===title);
      if(!item)return;
      const related=[...item.querySelectorAll('relatedArticles article')];
      if(!related.length)return;
      const box=document.createElement('div');box.className='related-coverage';
      box.innerHTML='<strong>Similar coverage:</strong>'+related.map(r=>{const t=r.querySelector('title')?.textContent||'';const l=r.querySelector('link')?.textContent||'#';const src=r.querySelector('source')?.textContent||'';return `<a href="${esc(l)}" target="_blank" rel="noopener noreferrer">${esc(t)}${src?' <span class="source">— '+esc(src)+'</span>':''}</a>`}).join('');
      card.appendChild(box);
    });
  }
  setInterval(decorate,1500);window.addEventListener('load',decorate);decorate();
})();
</script>'''

# Idempotently remove old copies.
for marker in ('related-coverage-v1','related-coverage-v1-style'):
    tag='<script id="'+marker+'">' if marker.endswith('v1') else '<style id="'+marker+'">'
    close='</script>' if marker.endswith('v1') else '</style>'
    while tag in s:
        a=s.find(tag); b=s.find(close,a)
        if b<0: break
        s=s[:a]+s[b+len(close):]

if '</head>' not in s: raise SystemExit('Missing </head>')
s=s.replace('</head>',STYLE+'\n</head>',1)
# This script needs the canonical renderer's allItems array; it does not alter rendering logic.
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Installed related-coverage footnotes.')
