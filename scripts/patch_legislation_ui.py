from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')

marker='<script id="legislation-ui-v1">'
while marker in s:
    a=s.find(marker); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]
style_marker='<style id="legislation-style-v1">'
while style_marker in s:
    a=s.find(style_marker); b=s.find('</style>',a)
    if b<0: break
    s=s[:a]+s[b+8:]

style=r'''<style id="legislation-style-v1">
.legislation-card .leg-top{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 9px}.leg-pill{display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;background:rgba(202,138,4,.09);border:1px solid rgba(202,138,4,.18);font-size:9px;font-weight:800;letter-spacing:.02em;color:#92400e}.leg-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:12px 0}.leg-field{padding:9px 10px;border:1px solid var(--ui-line);border-radius:10px;background:rgba(118,118,128,.035)}.leg-field strong{display:block;margin-bottom:3px;font-size:8px;letter-spacing:.08em;text-transform:uppercase;color:var(--ui-subtle)}.leg-field span{font-size:11.5px;line-height:1.45;color:var(--ui-muted)}.leg-support{margin-top:13px;padding-top:11px;border-top:1px solid var(--ui-line)}.leg-support-title{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ui-subtle);margin-bottom:6px}.leg-support a{display:block;padding:6px 0;text-decoration:none;font-size:11.5px;font-weight:650;border-top:1px solid rgba(60,60,67,.07)}.leg-support a:first-of-type{border-top:0}.leg-support small{display:block;margin-top:2px;color:var(--ui-subtle);font-size:9px}.leg-official{margin-top:10px}.leg-official a{display:inline-flex;padding:7px 10px;border-radius:9px;background:rgba(37,99,235,.07);border:1px solid rgba(37,99,235,.15);font-size:10px;font-weight:750;text-decoration:none}@media(max-width:600px){.leg-grid{grid-template-columns:1fr}.legislation-card .leg-top{gap:5px}}
</style>'''
s=s.replace('</head>',style+'\n</head>',1)

script=r'''<script id="legislation-ui-v1">
(function(){
  const insertAt=CANONICAL_SECTIONS.findIndex(x=>x[0]==='federal');
  if(!CANONICAL_SECTIONS.some(x=>x[0]==='legislation'))CANONICAL_SECTIONS.splice(insertAt>=0?insertAt+1:7,0,['legislation','📜 Laws & Legislation','#a16207']);
  sections=CANONICAL_SECTIONS;

  function xtext(item,tag){return item.querySelector(tag)?.textContent?.trim()||''}
  function renderLegislationCards(visible,total,count){
    const root=document.getElementById('news-feed'); if(!root)return;
    root.innerHTML='';
    const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent','#a16207');
    const head=document.createElement('div');head.className='section-header';
    head.innerHTML=`<h2>📜 Laws & Legislation</h2><span class="count">Showing ${count} of ${total} records</span>`;sec.appendChild(head);
    const intro=document.createElement('div');intro.className='x-issues-intro';intro.textContent='Official federal and New Mexico legislative records first. Congress.gov and the New Mexico Legislature provide the measure, status, latest action, and bill record; established news coverage is attached only as supporting context.';sec.appendChild(intro);
    const body=document.createElement('div');body.className='section-body';
    if(!visible.length)body.innerHTML='<div class="empty">No significant official legislation updates are available right now.</div>';
    visible.forEach((item,i)=>{
      const title=xtext(item,'title')||'Untitled'; const link=xtext(item,'link')||'#'; const source=xtext(item,'source'); const date=xtext(item,'pubDate');
      const jurisdiction=xtext(item,'jurisdiction')||'Federal'; const status=xtext(item,'status')||'Active development'; const what=xtext(item,'whatItDoes')||xtext(item,'description'); const affected=xtext(item,'whoAffected')||'See official record for details'; const effective=xtext(item,'effectiveDate')||'Not stated'; const next=xtext(item,'nextStep')||'Watch for the next formal action.'; const official=xtext(item,'officialSource'); const latest=xtext(item,'latestAction'); const sponsor=xtext(item,'sponsor');
      const related=[...item.querySelectorAll('relatedArticles > article')].slice(0,4);
      const ar=document.createElement('article');ar.className='news-item legislation-card';
      const support=related.length?`<div class="leg-support"><div class="leg-support-title">Supporting news coverage</div>${related.map(r=>{const rt=xtext(r,'title');const rl=xtext(r,'link');const rs=xtext(r,'source');return `<a href="${esc(rl)}" target="_blank" rel="noopener noreferrer">${esc(rt)}${rs?`<small>${esc(rs)}</small>`:''}</a>`}).join('')}</div>`:'';
      ar.innerHTML=`<div class="leg-top"><span class="leg-pill">${esc(jurisdiction)}</span><span class="leg-pill">${esc(status)}</span></div><h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${what?`<p class="description">${esc(what)}</p>`:''}<div class="leg-grid"><div class="leg-field"><strong>Who it affects</strong><span>${esc(affected)}</span></div><div class="leg-field"><strong>Effective date</strong><span>${esc(effective)}</span></div><div class="leg-field"><strong>What happens next</strong><span>${esc(next)}</span></div><div class="leg-field"><strong>Primary record</strong><span>${esc(source||'Official source')}</span></div>${latest?`<div class="leg-field"><strong>Latest official action</strong><span>${esc(latest)}</span></div>`:''}${sponsor?`<div class="leg-field"><strong>Sponsor</strong><span>${esc(sponsor)}</span></div>`:''}</div>${official?`<div class="leg-official"><a href="${esc(official)}" target="_blank" rel="noopener noreferrer">Open official record ↗</a></div>`:''}${support}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;
      body.appendChild(ar);
    });
    sec.appendChild(body);root.appendChild(sec);decorateNewBadges();
  }

  const baseLegislationRender=canonicalRender;
  canonicalRender=function(items){
    if(active!=='legislation')return baseLegislationRender(items);
    const data=paginatedNewsItems(items);
    renderLegislationCards(data.visible,data.available.length,data.count);
    appendLoadMoreControl(data);
    if(typeof syncDiscoveryButton==='function')syncDiscoveryButton();
  };
  render=canonicalRender;window.render=canonicalRender;window.canonicalRender=canonicalRender;
  canonicalBuildTabs();
})();
</script>'''
s=s.replace('</body>',script+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Added official-record-first Laws & Legislation cards with supporting news coverage.')
