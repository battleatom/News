from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

marker = '<script id="underreported-ui-v1">'
while marker in text:
    s = text.find(marker)
    e = text.find('</script>', s)
    if e < 0:
        break
    text = text[:s] + text[e + 9:]

script = r'''<script id="underreported-ui-v1">
const baseRenderForUnderreported=render;
function renderUnderreported(items){
 const def=sections.find(x=>x[0]==='underreported'),accent=def?def[2]:'#7c3aed';
 const list=items.filter(x=>(x.querySelector('category')?.textContent?.trim()||'')==='underreported');
 const root=document.getElementById('news-feed');root.innerHTML='';
 const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent',accent);
 const head=document.createElement('div');head.className='section-header';head.innerHTML=`<h2>🟣 Underreported</h2><span class="count">${list.length} stories · beyond the news cycle</span>`;sec.appendChild(head);
 const body=document.createElement('div');body.className='section-body';
 if(!list.length){body.innerHTML='<div class="empty">No underreported stories available right now.</div>';}
 list.forEach((item,i)=>{
   const ar=document.createElement('article');ar.className='news-item underreported-item';
   const title=item.querySelector('title')?.textContent||'Untitled',link=item.querySelector('link')?.textContent||'#';
   const desc=item.querySelector('description')?.textContent||'',why=item.querySelector('whyMatters')?.textContent||'';
   const happened=item.querySelector('whatHappened')?.textContent||'',missing=item.querySelector('whatIsMissing')?.textContent||'';
   const background=item.querySelector('background')?.textContent||'',next=item.querySelector('whatNext')?.textContent||'';
   const coverage=item.querySelector('coverage')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'',source=item.querySelector('source')?.textContent||'';
   let relatedHtml='';
   const related=item.querySelectorAll('related > article');
   if(related.length){
     relatedHtml='<div class="underreported-connections"><div class="underreported-label">Connections & footnotes</div>'+Array.from(related).map((r,j)=>{const rt=r.querySelector('title')?.textContent||'Related report',rl=r.querySelector('link')?.textContent||'#',rs=r.querySelector('source')?.textContent||'',rd=r.querySelector('pubDate')?.textContent||'';return `<div class="underreported-related"><span>${j+1}.</span><a href="${esc(rl)}" target="_blank" rel="noopener noreferrer">${esc(rt)}</a>${rs?`<small>${esc(rs)}${rd?' · '+esc(formatDate(rd)):''}</small>`:''}</div>`}).join('')+'</div>';
   }
   const fallback=happened||desc;
   ar.innerHTML=`<div class="underreported-topline"><span class="underreported-coverage">${esc(coverage||'🟡 Limited coverage')}</span></div><h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${fallback?`<div class="underreported-block"><div class="underreported-label">What happened</div><p>${esc(fallback)}</p></div>`:''}${why?`<div class="why"><strong>Why it matters</strong><br>${esc(why.replace(/^Why it matters:\s*/i,''))}</div>`:''}${missing?`<div class="underreported-block"><div class="underreported-label">What's being missed</div><p>${esc(missing)}</p></div>`:''}${background?`<div class="underreported-block"><div class="underreported-label">Background</div><p>${esc(background)}</p></div>`:''}${next?`<div class="underreported-block"><div class="underreported-label">What happens next</div><p>${esc(next)}</p></div>`:''}${relatedHtml}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;
   body.appendChild(ar);
 });
 sec.appendChild(body);root.appendChild(sec);
}
render=function(items){if(active==='underreported'){renderUnderreported(items);return}baseRenderForUnderreported(items)};
</script>'''
text=text.replace('</body>',script+'</body>',1)
path.write_text(text,encoding='utf-8')
print('Added richer Underreported story cards without changing the page layout.')
