from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

section_old = "const sections=[['top','🔴 Top Stories','#dc2626'],['nfl','🏈 NFL','#166534'],['x','𝕏 Top Issues','#111827'],['underreported','🟣 Underreported','#7c3aed'],['world','🌎 World','#2563eb'],['us','🇺🇸 United States','#1e3a8a'],['presidential','🏛️ Presidential','#b45309'],['federal','🏛️ Federal Government','#ca8a05'],['nm','🏜️ New Mexico','#0f766e'],['local','📍 Local / Four Corners','#15803d'],['region','🌎 Region','#2563eb'],['technology','💻 Technology','#0891b2'],['gaming','🎮 Gaming & Computing','#7c3aed'],['military','⚔️ Military & War','#991b1b']];"
section_alt = "const sections=[['top','🔴 Top Stories','#dc2626'],['nfl','🏈 NFL','#166534'],['x','𝕏 Top Issues','#111827'],['underreported','🟣 Underreported','#7c3aed'],['world','🌎 World','#2563eb'],['us','🇺🇸 United States','#1e3a8a'],['presidential','🏛️ Presidential','#b45309'],['federal','🏛️ Federal Government','#ca8a00'],['nm','🏜️ New Mexico','#0f766e'],['local','📍 Local / Four Corners','#15803d'],['region','🌎 Region','#2563eb'],['technology','💻 Technology','#0891b2'],['gaming','🎮 Gaming & Computing','#7c3aed'],['military','⚔️ Military & War','#991b1b']];"
# Leave the authoritative section declaration alone if it already contains X.
if "['x','𝕏 Top Issues','#111827']" not in text:
    text = text.replace("['nfl','🏈 NFL','#166534'],", "['nfl','🏈 NFL','#166534'],['x','𝕏 Top Issues','#111827'],", 1)

marker = '<script id="x-issues-ui-v1">'
while marker in text:
    s = text.find(marker); e = text.find('</script>', s)
    if e < 0: break
    text = text[:s] + text[e+9:]

script = r'''<script id="x-issues-ui-v1">
const baseRenderForX=render;
function renderXIssues(items){
 const list=items.filter(x=>(x.querySelector('category')?.textContent?.trim()||'')==='x');
 const root=document.getElementById('news-feed');root.innerHTML='';
 const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent','#111827');
 const head=document.createElement('div');head.className='section-header';head.innerHTML=`<h2>𝕏 What's Trending</h2><span class="count">${list.length} category leaders</span>`;sec.appendChild(head);
 const intro=document.createElement('div');intro.className='x-issues-intro';intro.textContent='One leading issue per category. X activity identifies the conversation; independent reporting provides the explanation. A conversation is not proof of a claim.';sec.appendChild(intro);
 const body=document.createElement('div');body.className='section-body';
 list.forEach((item,i)=>{
   const ar=document.createElement('article');ar.className='news-item x-issue-item';
   const title=item.querySelector('title')?.textContent||'Untitled',link=item.querySelector('link')?.textContent||'#';
   const desc=item.querySelector('description')?.textContent||'',topic=item.querySelector('xTopic')?.textContent||'Trending';
   const why=item.querySelector('xWhyTrending')?.textContent||'',people=item.querySelector('xWhatPeopleAreSaying')?.textContent||'',confirmed=item.querySelector('xConfirmed')?.textContent||'',unconfirmed=item.querySelector('xUnconfirmed')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'',source=item.querySelector('source')?.textContent||'';
   let relatedHtml=''; const related=item.querySelectorAll('xRelated > article');
   if(related.length){relatedHtml='<div class="x-related"><div class="underreported-label">Reporting & evidence</div>'+Array.from(related).map((r,j)=>{const t=r.querySelector('title')?.textContent||'Related reporting',l=r.querySelector('link')?.textContent||'#',s=r.querySelector('source')?.textContent||'';return `<div class="underreported-related"><span>${j+1}.</span><a href="${esc(l)}" target="_blank" rel="noopener noreferrer">${esc(t)}</a>${s?`<small>${esc(s)}</small>`:''}</div>`}).join('')+'</div>';}
   ar.innerHTML=`<div class="x-issue-meta"><span class="x-topic">${esc(topic)}</span><span class="x-signal">TOP X CONVERSATION</span></div><h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${desc?`<div class="underreported-block"><div class="underreported-label">What's happening</div><p>${esc(desc)}</p></div>`:''}${why?`<div class="underreported-block"><div class="underreported-label">Why it's trending</div><p>${esc(why)}</p></div>`:''}${people?`<div class="underreported-block"><div class="underreported-label">What people are saying</div><p>${esc(people)}</p></div>`:''}${confirmed?`<div class="x-confirmed"><strong>✓ What's confirmed</strong><p>${esc(confirmed)}</p></div>`:''}${unconfirmed?`<div class="x-unconfirmed"><strong>⚠️ What's not confirmed</strong><p>${esc(unconfirmed)}</p></div>`:''}${relatedHtml}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;
   body.appendChild(ar);
 });
 if(!list.length)body.innerHTML='<div class="empty">No X conversation met the requirements for publication right now.</div>';
 sec.appendChild(body);root.appendChild(sec);
}
render=function(items){if(active==='x'){renderXIssues(items);return}baseRenderForX(items)};
</script>'''
text=text.replace('</body>',script+'</body>',1)
path.write_text(text,encoding='utf-8')
print('Rebuilt X UI: one explainable issue per category.')
