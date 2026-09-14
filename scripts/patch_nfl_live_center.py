from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')

STYLE_MARK='/* nfl-live-center-v1 */'
style_anchor='<style id="nfl-live-style">'
a=s.find(style_anchor)
if a<0: raise SystemExit('NFL live center patch failed: nfl-live-style not found')
b=s.find('</style>',a)
if b<0: raise SystemExit('NFL live center patch failed: nfl-live-style end not found')
if STYLE_MARK not in s[a:b]:
    css=r'''/* nfl-live-center-v1 */
.nfl-live-center{display:block;overflow:visible!important;max-height:none!important;margin:0 0 12px;padding:12px 13px;border:1px solid rgba(15,23,42,.10);border-radius:16px;background:rgba(255,255,255,.78);box-shadow:0 8px 28px rgba(15,23,42,.07);backdrop-filter:saturate(140%) blur(18px);-webkit-backdrop-filter:saturate(140%) blur(18px)}
.nfl-live-center[hidden]{display:none!important}.nfl-live-center-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}.nfl-live-center-title{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:850;color:#0f172a;letter-spacing:-.01em}.nfl-live-center-meta{font-size:9px;font-weight:750;color:#94a3b8;white-space:nowrap}.nfl-live-selector{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}.nfl-live-selector button{appearance:none;border:1px solid rgba(100,116,139,.18);border-radius:999px;background:rgba(248,250,252,.82);padding:5px 8px;font:inherit;font-size:9.5px;font-weight:800;color:#64748b;cursor:pointer}.nfl-live-selector button.active{color:#111827;background:#fff;border-color:rgba(59,130,246,.25);box-shadow:0 2px 8px rgba(15,23,42,.07)}
.nfl-live-gamebar{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;padding:9px 10px;margin-bottom:8px;border-radius:12px;background:rgba(15,23,42,.035)}.nfl-live-gamebar-main{min-width:0}.nfl-live-gamebar-matchup{font-size:12.5px;font-weight:850;color:#111827;line-height:1.25}.nfl-live-gamebar-state{margin-top:2px;font-size:9.5px;font-weight:750;color:#64748b}.nfl-live-gamebar-score{font-size:18px;font-weight:900;letter-spacing:-.04em;color:#111827;white-space:nowrap}
.nfl-live-pulse{margin:0 0 8px;padding:7px 9px;border-radius:10px;background:rgba(37,99,235,.055);color:#475569;font-size:10px;line-height:1.4}.nfl-live-pulse strong{color:#2563eb}.nfl-live-plays{display:grid;gap:0;overflow:visible!important;max-height:none!important}.nfl-live-play{display:grid;grid-template-columns:56px minmax(0,1fr);gap:9px;padding:8px 2px;border-top:1px solid rgba(100,116,139,.11)}.nfl-live-play:first-child{border-top:0}.nfl-live-play-time{font-size:9px;font-weight:850;color:#94a3b8;line-height:1.35}.nfl-live-play-text{font-size:10.5px;font-weight:650;color:#334155;line-height:1.42}.nfl-live-center-msg{padding:7px 2px;color:#64748b;font-size:10.5px;line-height:1.4}
@media(prefers-color-scheme:dark){.nfl-live-center{background:rgba(18,24,34,.82);border-color:rgba(203,213,225,.12);box-shadow:0 10px 30px rgba(0,0,0,.24)}.nfl-live-center-title,.nfl-live-gamebar-matchup,.nfl-live-gamebar-score{color:#f1f5f9}.nfl-live-center-meta,.nfl-live-gamebar-state,.nfl-live-play-time{color:#8f9bad}.nfl-live-selector button{background:rgba(148,163,184,.07);border-color:rgba(203,213,225,.12);color:#aeb8c7}.nfl-live-selector button.active{background:rgba(255,255,255,.08);color:#fff;border-color:rgba(96,165,250,.28)}.nfl-live-gamebar{background:rgba(148,163,184,.06)}.nfl-live-pulse{background:rgba(59,130,246,.11);color:#c4ccd7}.nfl-live-pulse strong{color:#93c5fd}.nfl-live-play{border-color:rgba(203,213,225,.10)}.nfl-live-play-text,.nfl-live-center-msg{color:#cbd5e1}}
@media(max-width:600px){.nfl-live-center{padding:10px 10px;border-radius:14px;margin-bottom:10px}.nfl-live-center-head{margin-bottom:8px}.nfl-live-center-title{font-size:12px}.nfl-live-center-meta{font-size:8.5px}.nfl-live-selector{gap:5px;margin-bottom:8px}.nfl-live-selector button{font-size:9px;padding:5px 7px}.nfl-live-gamebar{padding:8px 9px}.nfl-live-gamebar-matchup{font-size:11.5px}.nfl-live-gamebar-score{font-size:16px}.nfl-live-play{grid-template-columns:50px minmax(0,1fr);gap:7px;padding:7px 1px}.nfl-live-play-text{font-size:10px}}
'''
    s=s[:b]+css+s[b:]

# The upcoming-window patch runs before this patch and may extend the note text.
# Match either form so these two patches remain order-compatible.
old_notes=(
    "Live:</strong> ESPN · current + upcoming 7 days · refreshes every 30 sec · kickoff times use your device timezone · finals roll off at 6:00 AM local",
    "Live:</strong> ESPN · refreshes every 30 sec · kickoff times use your device timezone · finals roll off at 6:00 AM local",
)
if "liveCenter.className='nfl-live-center'" not in s:
    matched=None
    for note_text in old_notes:
        candidate=f" const note=document.createElement('div');note.className='nfl-live-note';note.innerHTML='<strong>{note_text}';body.appendChild(note);\n const grid=document.createElement('div');grid.className='nfl-games-grid';body.appendChild(grid);"
        if candidate in s:
            matched=candidate
            replacement=f" const note=document.createElement('div');note.className='nfl-live-note';note.innerHTML='<strong>{note_text}';body.appendChild(note);\n const liveCenter=document.createElement('div');liveCenter.className='nfl-live-center';liveCenter.hidden=true;liveCenter.setAttribute('aria-live','polite');body.appendChild(liveCenter);\n const grid=document.createElement('div');grid.className='nfl-games-grid';body.appendChild(grid);"
            s=s.replace(candidate,replacement,1)
            break
    if matched is None:
        raise SystemExit('NFL live center patch failed: scoreboard layout anchor not found')

helper_anchor=" function logoMarkup(team,label){const src=team?.logo||team?.logos?.[0]?.href||'';return src?`<img src=\"${esc(src)}\" alt=\"${esc(label)} logo\" loading=\"lazy\">`:`<span class=\"nfl-logo-fallback\">${esc(team?.abbreviation||'NFL')}</span>`;}\n"
if 'function renderLivePlayCenter(' not in s:
    if helper_anchor not in s: raise SystemExit('NFL live center patch failed: helper anchor not found')
    helper=r''' let nflLiveFocusId='';
 function playClock(play){
  const period=Number(play?.period?.number||play?.period||0),clock=play?.clock?.displayValue||play?.clock||'';
  return [period?`Q${period}`:'',clock].filter(Boolean).join(' · ');
 }
 function collectLivePlays(summary){
  let plays=Array.isArray(summary?.plays)?summary.plays:[];
  if(!plays.length&&Array.isArray(summary?.drives?.current?.plays))plays=summary.drives.current.plays;
  if(!plays.length&&Array.isArray(summary?.drives?.previous))plays=summary.drives.previous.flatMap(d=>Array.isArray(d?.plays)?d.plays:[]);
  if(!plays.length&&Array.isArray(summary?.scoringPlays))plays=summary.scoringPlays;
  return plays.filter(p=>p&&(p.text||p.shortText)).slice(-4).reverse();
 }
 function pulseFromPlay(play){
  const t=String(play?.text||play?.shortText||'').trim();
  if(!t)return '';
  if(/touchdown/i.test(t))return 'Scoring swing: the latest sequence ended in a touchdown.';
  if(/intercept|fumble|turnover/i.test(t))return 'Momentum swing: the latest sequence produced a turnover.';
  if(/field goal/i.test(t))return 'Scoring update: the latest sequence ended with a field goal.';
  if(/punt/i.test(t))return 'Possession changed after the latest punt.';
  if(/two-point|2-point/i.test(t))return 'Conversion update: the latest sequence included a two-point attempt.';
  return 'Latest drive update from the live play feed.';
 }
 async function renderLivePlayCenter(events){
  const live=events.filter(ev=>ev.status?.type?.state==='in');
  if(!live.length){liveCenter.hidden=true;liveCenter.innerHTML='';nflLiveFocusId='';return;}
  if(!live.some(ev=>String(ev.id)===String(nflLiveFocusId)))nflLiveFocusId=String(live[0].id||'');
  const ev=live.find(x=>String(x.id)===String(nflLiveFocusId))||live[0],c=ev.competitions?.[0],teams=c?.competitors||[],away=teams.find(t=>t.homeAway==='away'),home=teams.find(t=>t.homeAway==='home');
  const awayLabel=away?.team?.abbreviation||away?.team?.shortDisplayName||'Away',homeLabel=home?.team?.abbreviation||home?.team?.shortDisplayName||'Home';
  const buttons=live.length>1?`<div class="nfl-live-selector">${live.map(x=>{const cc=x.competitions?.[0],tt=cc?.competitors||[],aa=tt.find(t=>t.homeAway==='away'),hh=tt.find(t=>t.homeAway==='home'),label=`${aa?.team?.abbreviation||'AWY'} @ ${hh?.team?.abbreviation||'HOME'}`;return `<button type="button" data-live-game="${esc(x.id||'')}" class="${String(x.id)===String(nflLiveFocusId)?'active':''}">${esc(label)}</button>`;}).join('')}</div>`:'';
  const detail=ev.status?.type?.shortDetail||ev.status?.type?.detail||'Live';
  liveCenter.hidden=false;
  liveCenter.innerHTML=`<div class="nfl-live-center-head"><div class="nfl-live-center-title"><span class="nfl-live-dot"></span>Live Play-by-Play</div><div class="nfl-live-center-meta">Updates every 30 sec</div></div>${buttons}<div class="nfl-live-gamebar"><div class="nfl-live-gamebar-main"><div class="nfl-live-gamebar-matchup">${esc(awayLabel)} at ${esc(homeLabel)}</div><div class="nfl-live-gamebar-state">${esc(detail)}</div></div><div class="nfl-live-gamebar-score">${esc(away?.score??'-')}–${esc(home?.score??'-')}</div></div><div class="nfl-live-center-msg">Loading latest plays…</div>`;
  liveCenter.querySelectorAll('[data-live-game]').forEach(btn=>btn.addEventListener('click',()=>{nflLiveFocusId=btn.dataset.liveGame||'';renderLivePlayCenter(events);}));
  try{
   const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event='+encodeURIComponent(ev.id)+'&ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('summary HTTP '+r.status);const summary=await r.json();
   if(String(ev.id)!==String(nflLiveFocusId))return;
   const plays=collectLivePlays(summary),pulse=plays[0]?pulseFromPlay(plays[0]):'';
   const oldMsg=liveCenter.querySelector('.nfl-live-center-msg');if(oldMsg)oldMsg.remove();
   if(pulse){const p=document.createElement('div');p.className='nfl-live-pulse';p.innerHTML=`<strong>Game pulse</strong> · ${esc(pulse)}`;liveCenter.appendChild(p);}
   const list=document.createElement('div');list.className='nfl-live-plays';
   if(!plays.length){list.innerHTML='<div class="nfl-live-center-msg">Live game detected. Play-by-play is not available yet.</div>';}
   else plays.forEach(play=>{const row=document.createElement('div');row.className='nfl-live-play';row.innerHTML=`<div class="nfl-live-play-time">${esc(playClock(play))}</div><div class="nfl-live-play-text">${esc(play.text||play.shortText||'')}</div>`;list.appendChild(row);});
   liveCenter.appendChild(list);
  }catch(err){const msg=liveCenter.querySelector('.nfl-live-center-msg');if(msg)msg.textContent='Live score is available; play-by-play is temporarily unavailable.';}
 }
'''
    s=s.replace(helper_anchor,helper_anchor+helper,1)

call_anchor="   const hasLive=events.some(ev=>ev.status?.type?.state==='in'),nextIndex=hasLive?-1:events.findIndex(ev=>ev.status?.type?.state==='pre');\n"
if 'await renderLivePlayCenter(events);' not in s:
    if call_anchor not in s: raise SystemExit('NFL live center patch failed: event render anchor not found')
    s=s.replace(call_anchor,call_anchor+'   await renderLivePlayCenter(events);\n',1)

P.write_text(s,encoding='utf-8')
print('Added non-scrolling Apple-style NFL live play-by-play center above scoreboard cards.')
