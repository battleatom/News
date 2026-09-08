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

# X tab is inserted after NFL and survives the collector's section enforcement.
old_sections = "const sections=[['top','🔴 Top Stories','#dc2626'],['nfl','🏈 NFL','#166534'],['underreported','🟣 Underreported','#7c3aed'],['world','🌎 World','#2563eb'],['us','🇺🇸 United States','#1e3a8a'],['presidential','🏛️ Presidential','#b45309'],['federal','🏛️ Federal Government','#ca8a04'],['nm','🏜️ New Mexico','#0f766e'],['local','📍 Local / Four Corners','#15803d'],['region','🌎 Region','#2563eb'],['technology','💻 Technology','#0891b2'],['gaming','🎮 Gaming & Computing','#7c3aed'],['military','⚔️ Military & War','#991b1b']];"
new_sections = "const sections=[['top','🔴 Top Stories','#dc2626'],['nfl','🏈 NFL','#166534'],['x','𝕏 Top Issues','#111827'],['underreported','🟣 Underreported','#7c3aed'],['world','🌎 World','#2563eb'],['us','🇺🇸 United States','#1e3a8a'],['presidential','🏛️ Presidential','#b45309'],['federal','🏛️ Federal Government','#ca8a04'],['nm','🏜️ New Mexico','#0f766e'],['local','📍 Local / Four Corners','#15803d'],['region','🌎 Region','#2563eb'],['technology','💻 Technology','#0891b2'],['gaming','🎮 Gaming & Computing','#7c3aed'],['military','⚔️ Military & War','#991b1b']];"
text=text.replace(old_sections,new_sections,1)

marker = '<script id="x-issues-ui-v1">'
while marker in text:
    s=text.find(marker); e=text.find('</script>',s)
    if e<0: break
    text=text[:s]+text[e+9:]

xscript = r'''<script id="x-issues-ui-v1">
const baseRenderForX=render;
function renderXIssues(items){
 const def=sections.find(x=>x[0]==='x'),accent=def?def[2]:'#111827';
 const list=items.filter(x=>(x.querySelector('category')?.textContent?.trim()||'')==='x');
 const root=document.getElementById('news-feed');root.innerHTML='';
 const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent',accent);
 const head=document.createElement('div');head.className='section-header';head.innerHTML=`<h2>𝕏 Top Issues</h2><span class="count">${list.length} issues · public conversation signals</span>`;sec.appendChild(head);
 const intro=document.createElement('div');intro.className='x-issues-intro';intro.textContent='A snapshot of issues gaining attention in publicly indexed X activity. Trending does not mean true: claims are labeled separately from verified reporting.';sec.appendChild(intro);
 const body=document.createElement('div');body.className='section-body';
 if(!list.length){body.innerHTML='<div class="empty">No strong X conversation signals were identified right now.</div>';}
 list.forEach((item,i)=>{
   const ar=document.createElement('article');ar.className='news-item x-issue-item';
   const title=item.querySelector('title')?.textContent||'Untitled',link=item.querySelector('link')?.textContent||'#';
   const desc=item.querySelector('description')?.textContent||'',topic=item.querySelector('xTopic')?.textContent||'';
   const signal=item.querySelector('xSignal')?.textContent||'Emerging signal',evidence=item.querySelector('xEvidence')?.textContent||'';
   const verification=item.querySelector('xVerification')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'';
   const source=item.querySelector('source')?.textContent||'';
   let relatedHtml=''; const related=item.querySelectorAll('xRelated > article');
   if(related.length){relatedHtml='<div class="x-related"><div class="underreported-label">Related reporting & posts</div>'+Array.from(related).map((r,j)=>{const t=r.querySelector('title')?.textContent||'Related result',l=r.querySelector('link')?.textContent||'#',s=r.querySelector('source')?.textContent||'';return `<div class="underreported-related"><span>${j+1}.</span><a href="${esc(l)}" target="_blank" rel="noopener noreferrer">${esc(t)}</a>${s?`<small>${esc(s)}</small>`:''}</div>`}).join('')+'</div>';}
   ar.innerHTML=`<div class="x-issue-meta"><span class="x-topic">${esc(topic)}</span><span class="x-signal">${esc(signal)}</span></div><h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${desc?`<div class="underreported-block"><div class="underreported-label">What's being discussed</div><p>${esc(desc)}</p></div>`:''}${evidence?`<div class="underreported-block"><div class="underreported-label">Signal</div><p>${esc(evidence)}</p></div>`:''}${verification?`<div class="x-verification"><strong>⚠️ Verification</strong><br>${esc(verification)}</div>`:''}${relatedHtml}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;
   body.appendChild(ar);
 });
 sec.appendChild(body);root.appendChild(sec);
}
render=function(items){if(active==='x'){renderXIssues(items);return}baseRenderForX(items)};
</script>'''
text=text.replace('</body>',xscript+'</body>',1)
path.write_text(text,encoding='utf-8')
print('Added richer Underreported cards and X Top Issues UI without changing the page layout.')
