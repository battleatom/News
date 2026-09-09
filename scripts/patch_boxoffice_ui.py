from pathlib import Path

P = Path("index.html")
MARKER = '<script id="boxoffice-location-v1">'
SCRIPT = r'''<script id="boxoffice-location-v1">
(function(){
  if(document.getElementById('boxoffice-location-v1')) return;
  const previousRender = render;
  const stateNames = {AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
  function localState(){
    const saved=(localStorage.getItem('underreported-location')||'').toUpperCase();
    const m=saved.match(/(?:^|,\s*)([A-Z]{2})$/);
    return m ? m[1] : '';
  }
  function safeUrl(u){try{const x=new URL(u,location.href);return /^https?:$/.test(x.protocol)?x.href:'#';}catch(e){return '#';}}
  function renderLocalBoxOffice(data){
    const root=document.getElementById('news-feed');
    const state=localState();
    const loc=(data.locations||{})[state]||null;
    const stateName=loc?.stateName||stateNames[state]||'your area';
    const movies=data.movies||[];
    root.innerHTML='';
    const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent','#9a3412');
    const head=document.createElement('div');head.className='section-header';
    head.innerHTML=`<h2>🎬 Box Office — ${esc(stateName)}</h2><span class="count">Movies, releases & local box-office news</span>`;sec.appendChild(head);
    const intro=document.createElement('div');intro.className='boxoffice-intro';
    intro.innerHTML=`Showing national movie releases plus box-office/theater news selected for <strong>${esc(stateName)}</strong>.${state==='NM'&&/Farmington/i.test(localStorage.getItem('underreported-location')||'')?' Local Farmington showtimes are included when available.':''}`;
    sec.appendChild(intro);
    const body=document.createElement('div');body.className='section-body';

    if(loc?.news?.length){
      const localTitle=document.createElement('div');localTitle.className='boxoffice-section-title';localTitle.textContent=`📍 ${stateName} Box Office & Theater News`;
      body.appendChild(localTitle);
      loc.news.forEach((n,i)=>{
        const ar=document.createElement('article');ar.className='news-item';
        ar.innerHTML=`<h3><a href="${esc(safeUrl(n.link))}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(n.title||'Untitled')}</a></h3>${n.description?`<p class="description">${esc(n.description)}</p>`:''}<div class="meta">${n.source?`<span class="source">${esc(n.source)}</span>`:''}${n.pubDate?`<span>${esc(formatDate(n.pubDate))}</span>`:''}</div>`;
        body.appendChild(ar);
      });
    }

    const nationalTitle=document.createElement('div');nationalTitle.className='boxoffice-section-title';nationalTitle.textContent='🎥 Movies & Releases';body.appendChild(nationalTitle);
    if(!movies.length){body.insertAdjacentHTML('beforeend','<div class="empty">Movie information is temporarily unavailable.</div>');}
    movies.forEach(movie=>{
      const card=document.createElement('article');card.className='news-item movie-card';
      const status=movie.status||'Upcoming';
      const localTheaters=movie.theaters||[];
      const showtimeHtml=localTheaters.length?`<div class="movie-showtimes"><strong>Local showtimes</strong>${localTheaters.map(t=>`<small>${esc(t.name||'Theater')}: ${esc((t.showtimes||[]).join(', '))}</small>`).join('')}</div>`:'';
      card.innerHTML=`<h3>${esc(movie.title||'Untitled')}</h3><div class="movie-details"><span class="movie-status">${esc(status)}</span>${movie.releaseDate?`<span class="movie-pill">Release: ${esc(movie.releaseDate)}</span>`:''}${movie.rating?`<span class="movie-pill">${esc(movie.rating)}</span>`:''}${movie.runtime?`<span class="movie-pill">${esc(movie.runtime)}</span>`:''}</div>${movie.description?`<p class="description">${esc(movie.description)}</p>`:''}${showtimeHtml}`;
      body.appendChild(card);
    });
    sec.appendChild(body);root.appendChild(sec);
  }
  function locationAwareRender(items){
    if(active!=='boxoffice') return previousRender(items);
    const root=document.getElementById('news-feed');root.innerHTML='<div class="loading">Loading location-specific Box Office…</div>';
    fetch('boxoffice.json?ts='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Box Office data unavailable');return r.json()}).then(data=>renderLocalBoxOffice(data)).catch(()=>{root.innerHTML='<div class="empty">Box Office information is temporarily unavailable.</div>'});
  }
  render=locationAwareRender;
})();
</script>'''

s = P.read_text(encoding='utf-8')
if MARKER in s:
    raise SystemExit('Box Office location patch already present')
s += '\n' + SCRIPT + '\n'
P.write_text(s, encoding='utf-8')
print('Added location-aware Box Office renderer.')
