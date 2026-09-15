from pathlib import Path

P = Path("index.html")
MARKER = '<script id="boxoffice-location-v1">'
SCRIPT = r'''<script id="boxoffice-location-v1">
(function(){
  if(window.__boxOfficeLocationV1===true) return;
  window.__boxOfficeLocationV1=true;
  const previousRender = render;
  const stateNames = {AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
  const DAY=86400000;
  function localState(){
    const saved=(localStorage.getItem('underreported-location')||'').toUpperCase();
    const m=saved.match(/(?:^|,\s*)([A-Z]{2})$/);
    return m ? m[1] : '';
  }
  function safeUrl(u){try{const x=new URL(u,location.href);return /^https?:$/.test(x.protocol)?x.href:'#';}catch(e){return '#';}}
  function ageRailClass(raw){const t=Date.parse(raw||'');if(!Number.isFinite(t))return '';const age=Math.max(0,(Date.now()-t)/DAY);if(age<=2)return 'rail-blue';if(age<=4)return 'rail-green';if(age<=7)return 'rail-orange';if(age<=10)return 'rail-purple';return 'rail-red';}
  function parseMovieDate(raw){if(!raw)return null;const d=new Date(`${raw}T12:00:00`);return Number.isFinite(d.getTime())?d:null;}
  function dayStart(d=new Date()){return new Date(d.getFullYear(),d.getMonth(),d.getDate());}
  function fmtMovieDate(raw){const d=parseMovieDate(raw);return d?new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',year:'numeric'}).format(d):'';}
  function ensureBoxOfficeStyles(){
    if(document.getElementById('boxoffice-release-status-style'))return;
    const st=document.createElement('style');st.id='boxoffice-release-status-style';st.textContent=`
      .boxoffice-status-key{display:flex;flex-wrap:wrap;gap:7px 10px;padding:9px 12px;margin:0 0 13px;border:1px solid var(--ui-line);border-radius:12px;background:rgba(248,250,252,.72);font-size:9.5px;font-weight:800;color:#64748b}
      .boxoffice-status-key span{display:inline-flex;align-items:center;gap:5px}.boxoffice-status-key i{width:9px;height:9px;border-radius:3px;display:inline-block}.boxoffice-status-key .cyan{background:#06b6d4}.boxoffice-status-key .blue{background:#2563eb}.boxoffice-status-key .green{background:#16a34a}.boxoffice-status-key .red{background:#dc2626}
      .movie-card.movie-rail-cyan{border-left:5px solid #06b6d4!important}.movie-card.movie-rail-blue{border-left:5px solid #2563eb!important}.movie-card.movie-rail-green{border-left:5px solid #16a34a!important}.movie-card.movie-rail-red{border-left:5px solid #dc2626!important}
      .movie-status.status-upcoming{background:rgba(6,182,212,.12);color:#0e7490}.movie-status.status-new{background:rgba(37,99,235,.11);color:#1d4ed8}.movie-status.status-playing{background:rgba(22,163,74,.11);color:#15803d}.movie-status.status-leaving{background:rgba(220,38,38,.11);color:#b91c1c}
      .movie-release-line{margin:1px 0 8px;color:#64748b;font-size:10.5px;font-weight:700;line-height:1.35}.movie-release-line strong{color:#334155}.movie-release-line .leave{color:#b91c1c;font-weight:850}
      .boxoffice-movie-group{margin:18px 0 8px;padding-left:10px;border-left:3px solid #64748b;font-size:14px;font-weight:850}.boxoffice-movie-group.now{border-left-color:#2563eb}.boxoffice-movie-group.upcoming{border-left-color:#06b6d4}
      @media(prefers-color-scheme:dark){.boxoffice-status-key{background:rgba(15,23,42,.42);color:#a7b0bd}.movie-release-line{color:#a7b0bd}.movie-release-line strong{color:#e5e7eb}.movie-status.status-upcoming{color:#67e8f9}.movie-status.status-new{color:#93c5fd}.movie-status.status-playing{color:#86efac}.movie-status.status-leaving{color:#fca5a5}}
    `;document.head.appendChild(st);
  }
  function movieState(movie){
    const today=dayStart();
    const release=parseMovieDate(movie.releaseDate);
    const leaving=parseMovieDate(movie.leavingDate);
    const status=(movie.status||'').toLowerCase();
    const upcoming=movie.isUpcoming===true||status.includes('upcoming')||(release&&dayStart(release)>today);
    if(upcoming)return {key:'upcoming',rail:'movie-rail-cyan',label:'Upcoming'};
    const leavingSoon=movie.leavingSoon===true||status.includes('leaving')||(leaving&&dayStart(leaving)>=today&&(dayStart(leaving)-today)/DAY<=7);
    if(leavingSoon)return {key:'leaving',rail:'movie-rail-red',label:'Leaving soon'};
    if(release){const age=(today-dayStart(release))/DAY;if(age>=0&&age<=14)return {key:'new',rail:'movie-rail-blue',label:'New release'};}
    return {key:'playing',rail:'movie-rail-green',label:'Now playing'};
  }
  function releaseSortValue(movie){const d=parseMovieDate(movie.releaseDate);return d?d.getTime():-Infinity;}
  function movieReleaseLine(movie,state){
    const release=parseMovieDate(movie.releaseDate),today=dayStart();
    const parts=[];
    if(release){
      const txt=fmtMovieDate(movie.releaseDate);
      if(state.key==='upcoming')parts.push(`<strong>Releases ${esc(txt)}</strong>`);
      else{
        const days=Math.max(1,Math.floor((today-dayStart(release))/DAY)+1);
        parts.push(`<strong>Released ${esc(txt)}</strong>`);
        if(days>0)parts.push(`${days} day${days===1?'':'s'} in theaters`);
      }
    }
    if(movie.leavingDate){const leave=fmtMovieDate(movie.leavingDate);if(leave)parts.push(`<span class="leave">Leaves theaters ${esc(leave)}</span>`);}
    return parts.length?`<div class="movie-release-line">${parts.join(' · ')}</div>`:'';
  }
  function renderMovieCard(movie,body){
    const state=movieState(movie);
    const card=document.createElement('article');card.className=`news-item movie-card ${state.rail}`;card.dataset.category='boxoffice';card.dataset.railMeaning='movie-status';
    const localTheaters=movie.theaters||[];
    const showtimeHtml=localTheaters.length?`<div class="movie-showtimes"><strong>Local showtimes</strong>${localTheaters.map(t=>`<small>${esc(t.name||'Theater')}: ${esc((t.showtimes||[]).join(', '))}</small>`).join('')}</div>`:'';
    card.innerHTML=`<h3>${esc(movie.title||'Untitled')}</h3><div class="movie-details"><span class="movie-status status-${state.key}">${esc(state.label)}</span>${movie.releaseDate?`<span class="movie-pill">${state.key==='upcoming'?'Release':'Released'}: ${esc(fmtMovieDate(movie.releaseDate))}</span>`:''}${movie.rating?`<span class="movie-pill">${esc(movie.rating)}</span>`:''}${movie.runtime?`<span class="movie-pill">${esc(movie.runtime)}</span>`:''}</div>${movieReleaseLine(movie,state)}${movie.description?`<p class="description">${esc(movie.description)}</p>`:''}${showtimeHtml}`;
    body.appendChild(card);
  }
  function renderLocalBoxOffice(data){
    ensureBoxOfficeStyles();
    const root=document.getElementById('news-feed');
    const state=localState();
    const loc=(data.locations||{})[state]||null;
    const stateName=loc?.stateName||stateNames[state]||'your area';
    const movies=data.movies||[];
    const current=movies.filter(m=>movieState(m).key!=='upcoming').sort((a,b)=>releaseSortValue(b)-releaseSortValue(a)||(a.title||'').localeCompare(b.title||''));
    const upcoming=movies.filter(m=>movieState(m).key==='upcoming').sort((a,b)=>releaseSortValue(a)-releaseSortValue(b)||(a.title||'').localeCompare(b.title||''));
    root.innerHTML='';
    const sec=document.createElement('section');sec.className='section';sec.dataset.category='boxoffice';sec.style.setProperty('--accent','#9a3412');
    const head=document.createElement('div');head.className='section-header';
    head.innerHTML=`<h2>🎬 Box Office — ${esc(stateName)}</h2><span class="count">Movies, releases & local box-office news</span>`;sec.appendChild(head);
    const intro=document.createElement('div');intro.className='boxoffice-intro';
    intro.innerHTML=`Showing national movie releases plus box-office/theater news selected for <strong>${esc(stateName)}</strong>.${state==='NM'&&/Farmington/i.test(localStorage.getItem('underreported-location')||'')?' Local Farmington showtimes are included when available.':''}`;
    sec.appendChild(intro);
    const body=document.createElement('div');body.className='section-body';
    const key=document.createElement('div');key.className='boxoffice-status-key';key.innerHTML='<span><i class="cyan"></i>Upcoming</span><span><i class="blue"></i>New release</span><span><i class="green"></i>Now playing</span><span><i class="red"></i>Leaving soon</span>';body.appendChild(key);

    if(current.length){
      const nowTitle=document.createElement('div');nowTitle.className='boxoffice-movie-group now';nowTitle.textContent='🎥 Now Playing — newest releases first';body.appendChild(nowTitle);
      current.forEach(movie=>renderMovieCard(movie,body));
    }
    if(upcoming.length){
      const upcomingTitle=document.createElement('div');upcomingTitle.className='boxoffice-movie-group upcoming';upcomingTitle.textContent='🩵 Coming Soon — next releases first';body.appendChild(upcomingTitle);
      upcoming.forEach(movie=>renderMovieCard(movie,body));
    }
    if(!movies.length){body.insertAdjacentHTML('beforeend','<div class="empty">Movie information is temporarily unavailable.</div>');}

    if(loc?.news?.length){
      const localTitle=document.createElement('div');localTitle.className='boxoffice-section-title';localTitle.textContent=`📍 ${stateName} Box Office & Theater News`;
      body.appendChild(localTitle);
      loc.news.forEach((n,i)=>{
        const ar=document.createElement('article');ar.className='news-item';ar.dataset.category='boxoffice';const newsAgeClass=ageRailClass(n.pubDate);if(newsAgeClass)ar.classList.add(newsAgeClass);ar.dataset.railMeaning='age';
        ar.innerHTML=`<h3><a href="${esc(safeUrl(n.link))}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(n.title||'Untitled')}</a></h3>${n.description?`<p class="description">${esc(n.description)}</p>`:''}<div class="meta">${n.source?`<span class="source">${esc(n.source)}</span>`:''}${n.pubDate?`<span>${esc(formatDate(n.pubDate))}</span>`:''}</div>`;
        body.appendChild(ar);
      });
    }
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
while MARKER in s:
    a=s.find(MARKER);b=s.find('</script>',a)
    if b<0: raise SystemExit('Malformed Box Office patch block')
    s=s[:a]+s[b+9:]
if '</body>' in s:
    s=s.replace('</body>',SCRIPT+'\n</body>',1)
else:
    s += '\n' + SCRIPT + '\n'
P.write_text(s, encoding='utf-8')
print('Installed location-aware Box Office renderer with release-status rails, release dates, and deterministic movie ordering.')
