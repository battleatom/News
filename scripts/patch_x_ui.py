from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")
marker = '<script id="x-issues-ui-v1">'
while marker in text:
    s = text.find(marker); e = text.find('</script>', s)
    if e < 0: break
    text = text[:s] + text[e+9:]

script = r'''<script id="x-issues-ui-v1">
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
text=text.replace('</body>',script+'</body>',1)
path.write_text(text,encoding='utf-8')
print('Added X Top Issues UI without changing the existing page layout.')
