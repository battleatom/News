from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
marker='<script id="nfl-live-v1">'
while marker in s:
    a=s.find(marker); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]

STYLE='''<style id="nfl-live-style">
.nfl-live-note{padding:8px 11px;margin-bottom:10px;border:1px solid var(--ui-line);border-radius:10px;background:rgba(255,255,255,.68);font-size:11px;line-height:1.35;color:#64748b}.nfl-live-note strong{color:#166534}
.nfl-games-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:8px}
.nfl-game-card{padding:10px 11px!important;min-height:126px!important;margin:0!important;display:flex;flex-direction:column;justify-content:space-between;gap:7px}
.nfl-game-card.nfl-next{box-shadow:0 0 0 2px rgba(22,101,52,.16)}
.nfl-game-top{display:flex;align-items:center;justify-content:space-between;gap:6px;min-height:18px}.nfl-badge{font-size:9px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#166534;background:rgba(22,163,74,.10);border-radius:999px;padding:3px 6px;white-space:nowrap}.nfl-badge.live{color:#b91c1c;background:rgba(239,68,68,.10)}.nfl-badge.final{color:#64748b;background:rgba(100,116,139,.10)}
.nfl-matchup{display:grid;gap:5px}.nfl-team-row{display:flex;align-items:flex-start;justify-content:space-between;gap:7px;min-width:0}.nfl-team-name{font-size:13px;font-weight:850;line-height:1.16;color:#0f172a;min-width:0}.nfl-team-score{font-size:16px;font-weight:900;line-height:1;color:#0f172a;flex:0 0 auto}.nfl-at{font-size:9px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em}
.nfl-game-meta{display:flex;align-items:flex-end;justify-content:space-between;gap:6px;margin-top:auto}.nfl-status{font-size:10px!important;font-weight:800;color:#64748b;line-height:1.25}.nfl-tv{font-size:10px;color:#475569;text-align:right;line-height:1.2}.nfl-tv a{font-size:10px}.nfl-live-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#16a34a;margin-right:5px;box-shadow:0 0 0 2px rgba(22,163,74,.12)}
@media(max-width:900px){.nfl-games-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.nfl-live-note{font-size:11px;padding:7px 9px;margin-bottom:8px}.nfl-games-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.nfl-game-card{padding:9px 9px!important;min-height:134px!important}.nfl-team-name{font-size:12.5px}.nfl-team-score{font-size:15px}.nfl-status,.nfl-tv,.nfl-tv a{font-size:9.5px}}
</style>'''
# Replace any previous NFL style block instead of stacking another override.
s=re.sub(r'<style id="nfl-live-style">.*?</style>', '', s, flags=re.S)
s=s.replace('</head>',STYLE+'\n</head>',1)

SCRIPT=r'''<script id="nfl-live-v1">
let nflRefreshTimer=null;
function renderNfl(){
 const root=document.getElementById('news-feed');root.innerHTML='';
 const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent','#166534');
 const h=document.createElement('div');h.className='section-header';h.innerHTML='<h2>🏈 NFL</h2><span class="count"><span class="nfl-live-dot"></span>Live scoreboard</span>';sec.appendChild(h);
 const body=document.createElement('div');body.className='section-body';body.innerHTML='<div class="loading">Loading live NFL scores…</div>';sec.appendChild(body);root.appendChild(sec);
 const note=document.createElement('div');note.className='nfl-live-note';note.innerHTML='<strong>Live:</strong> ESPN · refreshes every 30 sec';body.appendChild(note);
 const grid=document.createElement('div');grid.className='nfl-games-grid';body.appendChild(grid);
 function eventTime(ev){const t=Date.parse(ev.date||'');return Number.isFinite(t)?t:0;}
 function eventRank(ev){const state=ev.status?.type?.state;return state==='in'?0:state==='pre'?1:2;}
 function sortedEvents(events){
  return [...events].sort((a,b)=>{const ra=eventRank(a),rb=eventRank(b);if(ra!==rb)return ra-rb;const ta=eventTime(a),tb=eventTime(b);return ra===2?tb-ta:ta-tb;});
 }
 async function load(){
  try{
   const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=32&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('scoreboard HTTP '+r.status);const d=await r.json();
   [...body.querySelectorAll('.nfl-empty,.loading,.nfl-error')].forEach(x=>x.remove());grid.innerHTML='';
   if(!d.events?.length){const e=document.createElement('div');e.className='empty nfl-empty';e.textContent='No NFL games currently scheduled.';body.appendChild(e);return;}
   const events=sortedEvents(d.events);
   const hasLive=events.some(ev=>ev.status?.type?.state==='in');
   const nextIndex=hasLive?-1:events.findIndex(ev=>ev.status?.type?.state==='pre');
   events.forEach((ev,index)=>{
    const c=ev.competitions?.[0],ts=c?.competitors||[],a=ts.find(t=>t.homeAway==='away'),h=ts.find(t=>t.homeAway==='home');
    const state=ev.status?.type?.state,detail=ev.status?.type?.shortDetail||ev.status?.type?.detail||'Scheduled';
    const broadcasts=(c?.broadcasts||[]).flatMap(x=>x.names||[]).filter(Boolean);
    const watch=(ev.links||[]).find(x=>Array.isArray(x.rel)&&x.rel.some(r=>String(r).toLowerCase().includes('watch')));
    const when=state==='post'?'FINAL':detail;
    const awayName=esc(a?.team?.displayName||a?.team?.shortDisplayName||a?.team?.name||'Away');
    const homeName=esc(h?.team?.displayName||h?.team?.shortDisplayName||h?.team?.name||'Home');
    const awayScore=esc(a?.score??(state==='pre'?'0':'-')),homeScore=esc(h?.score??(state==='pre'?'0':'-'));
    const tv=broadcasts.length?esc(broadcasts.join(' · ')):'';
    const watchHtml=watch?.href?` <a href="${esc(watch.href)}" target="_blank" rel="noopener noreferrer">Watch</a>`:'';
    const card=document.createElement('article');card.className='news-item nfl-game-card';
    const isNext=index===nextIndex; if(isNext)card.classList.add('nfl-next');
    const badge=state==='in'?'<span class="nfl-badge live">LIVE</span>':isNext?'<span class="nfl-badge">NEXT</span>':state==='post'?'<span class="nfl-badge final">FINAL</span>':'<span></span>';
    card.innerHTML=`<div class="nfl-game-top">${badge}</div><div class="nfl-matchup"><div class="nfl-team-row"><span class="nfl-team-name">${awayName}</span><span class="nfl-team-score">${awayScore}</span></div><div class="nfl-at">at</div><div class="nfl-team-row"><span class="nfl-team-name">${homeName}</span><span class="nfl-team-score">${homeScore}</span></div></div><div class="nfl-game-meta"><span class="nfl-status">${esc(when)}</span>${tv?`<span class="nfl-tv">${tv}${watchHtml}</span>`:''}</div>`;
    grid.appendChild(card);
   });
  }catch(e){const old=body.querySelector('.nfl-error');if(!old){const err=document.createElement('div');err.className='empty nfl-error';err.textContent='NFL live data is temporarily unavailable; try Refresh.';body.appendChild(err);}}
 }
 load();if(nflRefreshTimer)clearInterval(nflRefreshTimer);nflRefreshTimer=setInterval(()=>{if(active==='nfl')load();},30000);
 const allNfl=allItems.filter(x=>(x.querySelector('category')?.textContent?.trim()||'')==='nfl');
 if(allNfl.length){const nh=document.createElement('div');nh.className='section-header';nh.style.marginTop='20px';nh.innerHTML=`<h2>NFL News</h2><span class="count">${allNfl.length} stories</span>`;root.appendChild(nh);const nb=document.createElement('div');nb.className='section-body';allNfl.slice(0,10).forEach((item,i)=>{const ar=document.createElement('article');ar.className='news-item';const title=item.querySelector('title')?.textContent||'Untitled',link=item.querySelector('link')?.textContent||'#',desc=item.querySelector('description')?.textContent||'',source=item.querySelector('source')?.textContent||'',date=item.querySelector('pubDate')?.textContent||'';ar.innerHTML=`<h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${desc?`<p class="description">${esc(desc)}</p>`:''}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;nb.appendChild(ar);});root.appendChild(nb);}
}

// canonicalRender already routes active==='nfl' through renderNfl(). Keeping the
// live renderer behind that one router avoids another wrapper around window.render.
window.renderNfl=renderNfl;

// A full browser reload can restore the saved NFL tab before the async News
// feed and all later renderer helpers are ready. Once the page is fully loaded,
// route through the final canonical window.render so the saved tab is restored.
function restoreNflAfterBrowserReload(attempt=0){
 if(typeof active==='undefined'||active!=='nfl')return;
 const itemsReady=typeof allItems!=='undefined'&&Array.isArray(allItems)&&allItems.length>0;
 if(!itemsReady){if(attempt<40)setTimeout(()=>restoreNflAfterBrowserReload(attempt+1),250);return;}
 const root=document.getElementById('news-feed');
 const alreadyRendered=!!root?.querySelector('.nfl-game-card');
 if(alreadyRendered)return;
 if(typeof window.render==='function')window.render(allItems);else renderNfl();
}
function scheduleSavedNflRestore(){setTimeout(()=>restoreNflAfterBrowserReload(0),75);}
if(document.readyState==='complete')scheduleSavedNflRestore();
else window.addEventListener('load',scheduleSavedNflRestore,{once:true});
</script>'''
s=s.replace('</body>',SCRIPT+'\n</body>',1)
p.write_text(s,encoding='utf-8')
print('Added compact ordered NFL scoreboard grid with full team names.')
