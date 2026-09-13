#!/usr/bin/env python3
from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

# Replace the canonical standard renderer with a render-bound V5 version.
# This makes hierarchy state part of each card at creation time rather than
# relying on a later MutationObserver pass to infer card meaning.
pattern = re.compile(r"function renderStandardCanonical\(items\)\{.*?\}\nfunction renderBoxOffice", re.S)

replacement = r'''function v5HierarchyKind(section,index){
  if(section==='underreported')return 'analysis';
  if(section==='x')return 'trending';
  if(section==='nm'||section==='local'||section==='region')return 'local';
  if(index===0&&['top','world','us','presidential','federal','military'].includes(section))return 'high';
  return 'standard';
}
function v5HierarchyLabel(kind){return ({high:'HIGH IMPACT',analysis:'ANALYSIS',local:'LOCAL',trending:'TRENDING',standard:'STANDARD'})[kind]||'STANDARD';}
function renderStandardCanonical(items){
 const def=CANONICAL_SECTIONS.find(x=>x[0]===active)||CANONICAL_SECTIONS[0];
 let list=items.filter(item=>(item.querySelector('category')?.textContent?.trim()||'world')===active);
 if(active==='region'&&typeof detectedRegion!=='undefined')list=list.filter(item=>(item.querySelector('region')?.textContent?.trim()||'')===detectedRegion);
 const root=document.getElementById('news-feed');root.innerHTML='';
 const sec=document.createElement('section');sec.className='section';sec.dataset.section=active;sec.style.setProperty('--accent',def[2]);
 const head=document.createElement('div');head.className='section-header';head.innerHTML=`<h2>${esc(def[1])}</h2><span class="count">${list.length} stories</span>`;sec.appendChild(head);
 const body=document.createElement('div');body.className='section-body';
 if(!list.length)body.innerHTML='<div class="empty">No stories available right now.</div>';
 list.forEach((item,i)=>{
   const ar=document.createElement('article');
   const title=item.querySelector('title')?.textContent||'Untitled',link=item.querySelector('link')?.textContent||'#',desc=item.querySelector('description')?.textContent||'',why=item.querySelector('whyMatters')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'',source=item.querySelector('source')?.textContent||'';
   const kind=v5HierarchyKind(active,i);
   ar.className=`news-item v5-hierarchy-${kind}`;
   ar.dataset.hierarchy=kind;
   ar.dataset.v5Hierarchy=kind;
   ar.dataset.section=active;
   ar.dataset.rank=String(i+1);
   ar.dataset.storyUrl=link;
   ar.dataset.publishedAt=date;
   ar.innerHTML=`<span class="v3-importance ${kind}" data-v5-hierarchy-badge="${kind}">${esc(v5HierarchyLabel(kind))}</span><h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${desc?`<p class="description">${esc(desc)}</p>`:''}${why?`<div class="why">${esc(why)}</div>`:''}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;
   body.appendChild(ar);
 });
 sec.appendChild(body);root.appendChild(sec);
 document.dispatchEvent(new CustomEvent('underreported:feed-rendered',{detail:{section:active,count:list.length}}));
 if(typeof window.decorateNewBadges==='function')window.decorateNewBadges();
}
function renderBoxOffice'''

if not pattern.search(s):
    raise SystemExit('Could not locate canonical standard renderer for V5 render binding')
s = pattern.sub(replacement, s, count=1)

P.write_text(s, encoding='utf-8')
print('Bound V5 hierarchy, raw story metadata, and feed-rendered event directly to canonical card creation.')
