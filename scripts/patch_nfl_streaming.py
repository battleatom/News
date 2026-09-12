from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

STYLE = '.nfl-stream{display:block;font-size:9.5px;font-weight:750;color:#166534;margin-top:2px}.nfl-stream-label{color:#64748b;font-weight:800}.nfl-stream a{font-size:9.5px}'
if STYLE not in s:
    s = s.replace('</style>', STYLE + '</style>', 1)

anchor = " function logoMarkup(team,label){const src=team?.logo||team?.logos?.[0]?.href||'';return src?`<img src=\"${esc(src)}\" alt=\"${esc(label)} logo\" loading=\"lazy\">`:`<span class=\"nfl-logo-fallback\">${esc(team?.abbreviation||'NFL')}</span>`;}\n"
helper = r''' function nflStreamingServices(broadcasts,ev){
  const names=(broadcasts||[]).map(x=>String(x||'').trim()).filter(Boolean),hay=names.join(' ').toUpperCase(),out=[];
  const add=x=>{if(x&&!out.includes(x))out.push(x);};
  if(hay.includes('NETFLIX'))add('Netflix');
  if(hay.includes('PRIME')||hay.includes('AMAZON'))add('Prime Video');
  if(hay.includes('PEACOCK'))add('Peacock');
  if(hay.includes('NBC'))add('Peacock');
  if(hay.includes('CBS'))add('Paramount+');
  if(hay.includes('FOX'))add('FOX One');
  if(hay.includes('ESPN+'))add('ESPN+');
  else if(hay.includes('ESPN')||hay.includes('ABC'))add('ESPN');
  if(hay.includes('NFL NETWORK'))add('NFL+');
  const t=Date.parse(ev?.date||''),d=Number.isFinite(t)?new Date(t):null;
  if(d&&d.getDay()===0&&(hay.includes('CBS')||hay.includes('FOX')))add('YouTube Sunday Ticket (out-of-market)');
  return out;
 }
'''
if 'function nflStreamingServices(' not in s:
    if anchor not in s:
        raise SystemExit('NFL streaming patch failed: logoMarkup anchor not found')
    s = s.replace(anchor, anchor + helper, 1)

old = "    const tv=broadcasts.length?esc(broadcasts.join(' · ')):'',watchHtml=watch?.href?` <a href=\"${esc(watch.href)}\" target=\"_blank\" rel=\"noopener noreferrer\">Watch</a>`:'';"
new = "    const tv=broadcasts.length?esc(broadcasts.join(' · ')):'',streams=nflStreamingServices(broadcasts,ev),streamHtml=streams.length?`<span class=\"nfl-stream\"><span class=\"nfl-stream-label\">Stream:</span> ${esc(streams.join(' · '))}</span>`:'',watchHtml=watch?.href?` <a href=\"${esc(watch.href)}\" target=\"_blank\" rel=\"noopener noreferrer\">Watch</a>`:'';"
if old in s:
    s = s.replace(old, new, 1)
elif 'streamHtml=streams.length' not in s:
    raise SystemExit('NFL streaming patch failed: TV metadata anchor not found')

old_card = "${tv?`<span class=\"nfl-tv\">${tv}${watchHtml}</span>`:''}</div>`;"
new_card = "${tv||streamHtml?`<span class=\"nfl-tv\">${tv?`<span class=\"nfl-airing\"><strong>Airing:</strong> ${tv}${watchHtml}</span>`:''}${streamHtml}</span>`:''}</div>`;"
if old_card in s:
    s = s.replace(old_card, new_card, 1)
elif 'class=\"nfl-airing\"' not in s:
    raise SystemExit('NFL streaming patch failed: card metadata anchor not found')

p.write_text(s, encoding='utf-8')
print('Added per-game NFL streaming availability beside broadcast information.')
