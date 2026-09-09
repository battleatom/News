from pathlib import Path
import re

P=Path('scripts/update_news.py')
s=P.read_text(encoding='utf-8')

# Persist related stories in RSS so the generated page can show the alternate coverage.
old="""        out += [\"<item>\", f'<title>{xml_escape(item[\"title\"])}</title>', f'<link>{xml_escape(item[\"link\"])}</link>', f'<description>{xml_escape(item.get(\"description\", \"\"))}</description>', f'<pubDate>{xml_escape(item[\"pubDate\"])}</pubDate>', f'<source>{xml_escape(item[\"source\"])}</source>', f'<category>{item[\"category\"]}</category>', f'<region>{xml_escape(item.get(\"region\", \"\"))}</region>', f'<whyMatters>{xml_escape(item.get(\"whyMatters\", \"\"))}</whyMatters>', f'<guid isPermaLink=\"false\">{guid}</guid>', \"</item>\"]"""
new="""        out += [\"<item>\", f'<title>{xml_escape(item[\"title\"])}</title>', f'<link>{xml_escape(item[\"link\"])}</link>', f'<description>{xml_escape(item.get(\"description\", \"\"))}</description>', f'<pubDate>{xml_escape(item[\"pubDate\"])}</pubDate>', f'<source>{xml_escape(item[\"source\"])}</source>', f'<category>{item[\"category\"]}</category>', f'<region>{xml_escape(item.get(\"region\", \"\"))}</region>', f'<whyMatters>{xml_escape(item.get(\"whyMatters\", \"\"))}</whyMatters>']
        related=item.get('_relatedArticles', [])
        if related:
            out.append('<relatedArticles>')
            for rel in related:
                out += [f'<article><title>{xml_escape(rel.get(\"title\",\"\"))}</title>', f'<link>{xml_escape(rel.get(\"link\",\"\"))}</link>', f'<source>{xml_escape(rel.get(\"source\",\"\"))}</source></article>']
            out.append('</relatedArticles>')
        out += [f'<guid isPermaLink=\"false\">{guid}</guid>', \"</item>\"]"""
if old in s:
    s=s.replace(old,new,1)
elif '<relatedArticles>' not in s:
    raise SystemExit('Could not locate RSS item builder')
P.write_text(s,encoding='utf-8')
print('Related article clusters will be persisted in the RSS feed.')

# Patch the generated page renderer to display related coverage as a compact footnote.
I=Path('index.html')
s=I.read_text(encoding='utf-8')
marker='related-coverage-v1'
while True:
    a=s.find('<script id="'+marker+'">')
    if a<0: break
    b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]
style_id=marker+'-style'
while True:
    a=s.find('<style id="'+style_id+'">')
    if a<0: break
    b=s.find('</style>',a)
    if b<0: break
    s=s[:a]+s[b+8:]

STYLE='''<style id="related-coverage-v1-style">.related-coverage{margin:9px 0 0;padding:8px 10px;border-top:1px solid var(--ui-line);font-size:10px;color:#64748b}.related-coverage strong{color:#475569}.related-coverage a{display:block;margin-top:4px;color:#475569;text-decoration:underline}.related-coverage .source{color:#94a3b8}</style>'''
SCRIPT=r'''<script id="related-coverage-v1">
(function(){
  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
  function decorate(){
    document.querySelectorAll('.news-item').forEach(card=>{
      if(card.querySelector('.related-coverage'))return;
      const titleEl=card.querySelector('h3 a'); if(!titleEl)return;
      const title=titleEl.textContent.replace(/^\d+\.\s*/,'').trim();
      const matches=(window.allItems||[]).filter(item=>{
        const t=item.querySelector('title')?.textContent?.trim()||'';
        return t!==title && item.querySelector('relatedArticles')?.querySelector('article');
      });
      // The canonical renderer below reads the relatedArticles nodes directly when present.
      const related=[];
      for(const item of matches){
        if((item.querySelector('title')?.textContent||'').trim()!==title)continue;
        item.querySelectorAll('relatedArticles article').forEach(a=>related.push({title:a.querySelector('title')?.textContent||'',link:a.querySelector('link')?.textContent||'#',source:a.querySelector('source')?.textContent||''}));
      }
      if(!related.length)return;
      const box=document.createElement('div');box.className='related-coverage';box.innerHTML='<strong>Similar coverage:</strong>'+related.map(x=>`<a href="${esc(x.link)}" target="_blank" rel="noopener noreferrer">${esc(x.title)}${x.source?' <span class="source">— '+esc(x.source)+'</span>':''}</a>`).join('');card.appendChild(box);
    });
  }
  window.addEventListener('load',decorate); setInterval(decorate,2000);
})();
</script>'''
# The canonical renderer has direct access to parsed XML items. Add the footnote in renderStandardCanonical.
needle="body.appendChild(ar)});sec.appendChild(body);"
replacement="body.appendChild(ar)});\n    list.forEach((item,i)=>{const related=[...item.querySelectorAll('relatedArticles article')];if(!related.length)return;const cards=body.querySelectorAll('.news-item');const card=cards[i];if(!card)return;const box=document.createElement('div');box.className='related-coverage';box.innerHTML='<strong>Similar coverage:</strong>'+related.map(r=>{const t=r.querySelector('title')?.textContent||'';const l=r.querySelector('link')?.textContent||'#';const src=r.querySelector('source')?.textContent||'';return `<a href=\"${esc(l)}\" target=\"_blank\" rel=\"noopener noreferrer\">${esc(t)}${src?' <span class=\"source\">— '+esc(src)+'</span>':''}</a>`}).join('');card.appendChild(box);});sec.appendChild(body);"
if needle in s:
    s=s.replace(needle,replacement,1)
else:
    raise SystemExit('Could not locate standard article renderer')
s=s.replace('</head>',STYLE+'\n</head>',1)
I.write_text(s,encoding='utf-8')
print('Installed similar-coverage footnotes on generated article cards.')
