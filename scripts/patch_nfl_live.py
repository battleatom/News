from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
marker='<script id="nfl-live-v1">'
while marker in s:
    a=s.find(marker); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]

STYLE='''<style id="nfl-live-style">.nfl-live-note{padding:3px 6px;margin-bottom:4px;border:1px solid var(--ui-line);border-radius:7px;background:rgba(255,255,255,.68);font-size:7px;line-height:1.1;color:#64748b}.nfl-live-note strong{color:#166534}.nfl-game-card{padding:3px 6px!important;min-height:0!important;margin:0!important}.nfl-score-line{display:flex;align-items:center;gap:4px;min-width:0;white-space:nowrap;font-size:8px!important;line-height:1.05!important;color:#334155}.nfl-score-line .teams{font-weight:800;color:#0f172a}.nfl-score-line .status{color:#64748b}.nfl-score-line .tv{margin-left:auto;overflow:hidden;text-overflow:ellipsis;color:#475569;font-size:7px}.nfl-score-line a{font-size:7px}.nfl-live-dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:#16a34a;margin-right:4px;box-shadow:0 0 0 2px rgba(22,163,74,.12)}</style>'''
s=s.replace('</head>',STYLE+'\n</head>',1)

SCRIPT=r'''<script id="nfl-live-v1">
let nflRefreshTimer=null;
function renderNflLive(){
 const root=document.getElementById('news-feed');root.innerHTML='';
 const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent','#166534');
 const h=document.createElement('div');h.className='section-header';h.innerHTML='<h2>🏈 NFL</h2><span class="count"><span class="nfl-live-dot"></span>Live scoreboard</span>';sec.appendChild(h);
 const body=document.createElement('div');body.className='section-body';body.innerHTML='<div class="loading">Loading live NFL scores…</div>';sec.appendChild(body);root.appendChild(sec);
 const note=document.createElement('div');note.className='nfl-live-note';note.innerHTML='<strong>Live:</strong> ESPN · refreshes every 30 sec';body.appendChild(note);
 async function load(){
  try{
   const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);const d=await r.json();
   [...body.querySelectorAll('.nfl-game-card,.nfl-empty')].forEach(x=>x.remove());
   if(!d.events?.length){const e=document.createElement('div');e.className='empty nfl-empty';e.textContent='No NFL games currently scheduled.';body.appendChild(e);return;}
   d.events.forEach(ev=>{const c=ev.competitions?.[0],ts=c?.competitors||[],a=ts.find(t=>t.homeAway==='away'),h=ts.find(t=>t.homeAway==='home');const card=document.createElement('article');card.className='news-item nfl-game-card';const state=ev.status?.type?.state,detail=ev.status?.type?.shortDetail||ev.status?.type?.detail||'Scheduled';const broadcasts=(c?.broadcasts||[]).flatMap(x=>x.names||[]).filter(Boolean);const watch=(ev.links||[]).find(x=>Array.isArray(x.rel)&&x.rel.some(r=>String(r).toLowerCase().includes('watch')));const when=state==='post'?'FINAL':detail;const away=esc(a?.team?.abbreviation||a?.team?.shortDisplayName||'AWAY'),home=esc(h?.team?.abbreviation||h?.team?.shortDisplayName||'HOME');const tv=broadcasts.length?esc(broadcasts.join(' · ')):'';const watchHtml=watch?.href?` <a href="${esc(watch.href)}" target="_blank" rel="noopener noreferrer">Watch</a>`:'';card.innerHTML=`<div class="nfl-score-line"><span class="teams">${away} ${esc(a?.score??'-')} @ ${home} ${esc(h?.score??'-')}</span><span class="status">· ${esc(when)}</span>${tv?`<span class="tv">· ${tv}${watchHtml}</span>`:''}</div>`;body.appendChild(card);});
  }catch(e){const old=body.querySelector('.nfl-error');if(!old){const err=document.createElement('div');err.className='empty nfl-error';err.textContent='NFL live data is temporarily unavailable; try Refresh.';body.appendChild(err);}}
 }
 load();if(nflRefreshTimer)clearInterval(nflRefreshTimer);nflRefreshTimer=setInterval(()=>{if(active==='nfl')load();},30000);
 const allNfl=allItems.filter(x=>(x.querySelector('category')?.textContent?.trim()||'')==='nfl');
 if(allNfl.length){const nh=document.createElement('div');nh.className='section-header';nh.style.marginTop='20px';nh.innerHTML=`<h2>NFL News</h2><span class="count">${allNfl.length} stories</span>`;root.appendChild(nh);const nb=document.createElement('div');nb.className='section-body';allNfl.slice(0,10).forEach((item,i)=>{const ar=document.createElement('article');ar.className='news-item';const title=item.querySelector('title')?.textContent||'Untitled',link=item.querySelector('link')?.textContent||'#',desc=item.querySelector('description')?.textContent||'',source=item.querySelector('source')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'';ar.innerHTML=`<h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${desc?`<p class="description">${esc(desc)}</p>`:''}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;nb.appendChild(ar);});root.appendChild(nb);}
}
const canonicalBeforeNfl=canonicalRender;
canonicalRender=function(items){if(active==='nfl'){renderNflLive();return}canonicalBeforeNfl(items);};
window.render=canonicalRender;
</script>'''
s=s.replace('</body>',SCRIPT+'\n</body>',1)
p.write_text(s,encoding='utf-8')
print('Added ultra-compact single-line NFL live scoreboard with 30-second refresh.')
