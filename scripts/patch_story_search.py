from pathlib import Path
import re

path = Path('index.html')
text = path.read_text(encoding='utf-8')

STYLE = r'''<style id="story-search-v1-style">
#story-search{margin-left:auto;width:clamp(150px,22vw,290px);min-width:0;box-sizing:border-box;border:1px solid #334155;border-radius:9px;background:#0f172a;color:#f8fafc;padding:7px 10px;font-size:12px;line-height:1.2;outline:none}
#story-search::placeholder{color:#94a3b8}
#story-search:focus{border-color:#64748b;box-shadow:0 0 0 2px rgba(148,163,184,.15)}
#story-search[disabled]{opacity:.55;cursor:not-allowed}
@media(max-width:700px){.toolbar{flex-wrap:wrap}#story-search{order:20;margin-left:0;width:100%;flex:1 1 100%}}
</style>
'''

HTML = '<input id="story-search" type="search" inputmode="search" autocomplete="off" placeholder="Search stories…" aria-label="Search stories in this section">'

SCRIPT = r'''<script id="story-search-v1">
(function(){
  'use strict';
  const input=document.getElementById('story-search');
  if(!input || typeof render!=='function')return;

  let query='';
  const baseRender=render;
  const unsupported=new Set(['nfl','boxoffice']);

  function itemText(item){
    if(!item || !item.querySelectorAll)return '';
    const selectors='title,description,source,whyMatters,region,impact,category,whatItDoes,whoAffected,latestAction,sponsor,jurisdiction,status';
    return [...item.querySelectorAll(selectors)].map(el=>el.textContent||'').join(' ').toLowerCase();
  }

  function filtered(items){
    const q=query.trim().toLowerCase();
    if(!q || !Array.isArray(items))return items;
    return items.filter(item=>itemText(item).includes(q));
  }

  function syncAvailability(){
    const blocked=unsupported.has(String(active||''));
    input.disabled=blocked;
    input.placeholder=blocked?'Search unavailable in this live section':'Search stories…';
  }

  render=function(items){
    syncAvailability();
    return baseRender(unsupported.has(String(active||''))?items:filtered(items));
  };

  input.addEventListener('input',function(){
    query=input.value||'';
    render(allItems);
  });
  input.addEventListener('keydown',function(event){
    if(event.key==='Escape' && input.value){
      input.value='';query='';render(allItems);input.blur();
    }
  });
  document.addEventListener('keydown',function(event){
    if(event.key==='/' && !event.ctrlKey && !event.metaKey && !event.altKey){
      const tag=(document.activeElement?.tagName||'').toLowerCase();
      if(tag!=='input' && tag!=='textarea' && !input.disabled){event.preventDefault();input.focus();}
    }
  });
  syncAvailability();
})();
</script>
'''

# Idempotently remove the prior generated search blocks.
text = re.sub(r'<style id="story-search-v1-style">.*?</style>\s*', '', text, flags=re.S)
text = re.sub(r'<script id="story-search-v1">.*?</script>\s*', '', text, flags=re.S)
text = re.sub(r'<input id="story-search"[^>]*>\s*', '', text, flags=re.S)

if '</head>' not in text or '</body>' not in text:
    raise SystemExit('Expected HTML structure not found')

text = text.replace('</head>', STYLE + '</head>', 1)
status = '<span id="status">Loading…</span>'
if status not in text:
    raise SystemExit('Toolbar status anchor not found')
text = text.replace(status, status + HTML, 1)
text = text.replace('</body>', SCRIPT + '</body>', 1)

path.write_text(text, encoding='utf-8')
print('Story search UI applied.')
