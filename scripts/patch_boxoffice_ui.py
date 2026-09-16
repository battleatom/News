from pathlib import Path

P = Path("index.html")
MARKER = '<script id="boxoffice-location-v1">'
SCRIPT = r'''<script id="boxoffice-location-v1">
(function(){
  if(window.__boxOfficeLocationV1===true) return;
  window.__boxOfficeLocationV1=true;
  const previousRender = render;
  const previousCanonicalRender = typeof canonicalRender==='function' ? canonicalRender : null;
  const stateNames = {AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
  const DAY=86400000;
  const BOXOFFICE_INITIAL_BATCH=8;
  const BOXOFFICE_NEXT_BATCH=8;
  const BOXOFFICE_CACHE_MS=5*60*1000;
  let boxOfficeCache=null;
  let boxOfficeCacheAt=0;
  let boxOfficeRequest=null;

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
      .movie-release-line{margin:1px 0 8px;color:#64748b;font-size:10.5px;font-weight:700;line-height:1.35}.movie-release-line strong{color:#334155}.movie-release-line .leave{color:#b91c1c;font-weight:850}.movie-release-line .confirmed{color:#64748b;font-weight:800}
      .boxoffice-movie-group{margin:18px 0 8px;padding-left:10px;border-left:3px solid #64748b;font-size:14px;font-weight:850}.boxoffice-movie-group.now{border-left-color:#2563eb}.boxoffice-movie-group.upcoming{border-left-color:#06b6d4}
      .movie-card .movie-news{margin-top:10px;font-size:.82rem;line-height:1.38}.movie-card .movie-news .underreported-label{font-size:.72rem!important;letter-spacing:.08em}.movie-card .movie-news a{display:block;margin-top:6px;font-size:.82rem!important;line-height:1.38!important;font-weight:600!important;text-decoration-thickness:1px}
      .boxoffice-scroll-sentinel{min-height:34px;display:flex;align-items:center;justify-content:center;margin:10px 0;color:#64748b;font-size:.78rem;font-weight:750;letter-spacing:.01em}
      .boxoffice-scroll-sentinel::after{content:'Loading more Box Office…'}
      .boxoffice-endcap{margin:14px 0 4px;padding:12px;text-align:center;border-top:1px solid var(--ui-line);color:#64748b;font-size:.76rem;font-weight:750}
      @media(prefers-color-scheme:dark){.boxoffice-status-key{background:rgba(15,23,42,.42);color:#a7b0bd}.movie-release-line{color:#a7b0bd}.movie-release-line strong{color:#e5e7eb}.movie-release-line .confirmed{color:#a7b0bd}.movie-status.status-upcoming{color:#67e8f9}.movie-status.status-new{color:#93c5fd}.movie-status.status-playing{color:#86efac}.movie-status.status-leaving{color:#fca5a5}.boxoffice-scroll-sentinel,.boxoffice-endcap{color:#a7b0bd}}
      @media(max-width:700px){.movie-card .movie-news a{font-size:.8rem!important;line-height:1.36!important}}
    `;document.head.appendChild(st);
  }
  function movieState(movie){
    const today=dayStart();
    const release=parseMovieDate(movie.releaseDate);
    const leaving=parseMovieDate(movie.leavingDate);
    const status=(movie.status||'').toLowerCase();
    const upcoming=movie.isUpcoming===true||status.includes('upcoming')||(release&&dayStart(release)>today);
    if(upcoming)return {key:'upcoming',rail:'movie-rail-cyan',label:'Coming soon'};
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
    if(movie.leavingDate){
      const leave=fmtMovieDate(movie.leavingDate);
      if(leave)parts.push(`<span class="leave">Last confirmed local showtime ${esc(leave)}</span>`);
    }else if(movie.confirmedThrough && state.key!=='upcoming'){
      const through=fmtMovieDate(movie.confirmedThrough);
      if(through)parts.push(`<span class="confirmed">Showtimes confirmed through ${esc(through)}</span>`);
    }
    return parts.length?`<div class="movie-release-line">${parts.join(' · ')}</div>`:'';
  }
  function renderMovieCard(movie,target){
    const state=movieState(movie);
    const card=document.createElement('article');card.className=`news-item movie-card ${state.rail}`;card.dataset.category='boxoffice';card.dataset.railMeaning='movie-status';
    const localTheaters=movie.theaters||[];
    const showtimeHtml=localTheaters.length?`<div class="movie-showtimes"><strong>Local showtimes</strong>${localTheaters.map(t=>`<small>${esc(t.name||'Theater')}: ${esc((t.showtimes||[]).join(', '))}</small>`).join('')}</div>`:'';
    const movieNews=(movie.news||[]).slice(0,3);
    const newsHtml=movieNews.length?`<div class="movie-news"><div class="underreported-label">Movie news</div>${movieNews.map(n=>`<a href="${esc(safeUrl(n.link))}" target="_blank" rel="noopener noreferrer">${esc(n.title||'Movie news')}</a>`).join('')}</div>`:'';
    card.innerHTML=`<h3>${esc(movie.title||'Untitled')}</h3><div class="movie-details"><span class="movie-status status-${state.key}">${esc(state.label)}</span>${movie.releaseDate?`<span class="movie-pill">${state.key==='upcoming'?'Release':'Released'}: ${esc(fmtMovieDate(movie.releaseDate))}</span>`:''}${movie.rating?`<span class="movie-pill">${esc(movie.rating)}</span>`:''}${movie.runtime?`<span class="movie-pill">${esc(movie.runtime)}</span>`:''}</div>${movieReleaseLine(movie,state)}${movie.description?`<p class="description">${esc(movie.description)}</p>`:''}${showtimeHtml}${newsHtml}`;
    target.appendChild(card);
  }
  function renderLocalNewsCard(n,i,target){
    const ar=document.createElement('article');ar.className='news-item';ar.dataset.category='boxoffice';const newsAgeClass=ageRailClass(n.pubDate);if(newsAgeClass)ar.classList.add(newsAgeClass);ar.dataset.railMeaning='age';
    ar.innerHTML=`<h3><a href="${esc(safeUrl(n.link))}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(n.title||'Untitled')}</a></h3>${n.description?`<p class="description">${esc(n.description)}</p>`:''}<div class="meta">${n.source?`<span class="source">${esc(n.source)}</span>`:''}${n.pubDate?`<span>${esc(formatDate(n.pubDate))}</span>`:''}</div>`;
    target.appendChild(ar);
  }
  function disconnectBoxOfficeObserver(){
    if(window.__boxOfficeScrollObserver){try{window.__boxOfficeScrollObserver.disconnect()}catch(e){}window.__boxOfficeScrollObserver=null;}
  }
  function renderLocalBoxOffice(data){
    ensureBoxOfficeStyles();
    disconnectBoxOfficeObserver();
    const root=document.getElementById('news-feed');
    const state=localState();
    const loc=(data.locations||{})[state]||null;
    const stateName=loc?.stateName||stateNames[state]||'your area';
    const movies=data.movies||[];
    const current=movies.filter(m=>movieState(m).key!=='upcoming').sort((a,b)=>releaseSortValue(b)-releaseSortValue(a)||(a.title||'').localeCompare(b.title||''));
    const upcoming=movies.filter(m=>movieState(m).key==='upcoming').sort((a,b)=>releaseSortValue(a)-releaseSortValue(b)||(a.title||'').localeCompare(b.title||''));
    const localNews=loc?.news||[];
    root.innerHTML='';
    const sec=document.createElement('section');sec.className='section';sec.dataset.category='boxoffice';sec.style.setProperty('--accent','#9a3412');
    const head=document.createElement('div');head.className='section-header';
    head.innerHTML=`<h2>🎬 Box Office — ${esc(stateName)}</h2><span class="count">Loading Box Office cards…</span>`;sec.appendChild(head);
    const countEl=head.querySelector('.count');
    const intro=document.createElement('div');intro.className='boxoffice-intro';
    intro.innerHTML=`Showing national movie releases plus box-office/theater news selected for <strong>${esc(stateName)}</strong>.${state==='NM'&&/Farmington/i.test(localStorage.getItem('underreported-location')||'')?' Local Farmington showtimes are included when available.':''}`;
    sec.appendChild(intro);
    const body=document.createElement('div');body.className='section-body';
    const key=document.createElement('div');key.className='boxoffice-status-key';key.innerHTML='<span><i class="cyan"></i>Coming soon</span><span><i class="blue"></i>New release</span><span><i class="green"></i>Now playing</span><span><i class="red"></i>Leaving soon</span>';body.appendChild(key);

    const queue=[];
    if(current.length){
      queue.push({type:'heading',className:'boxoffice-movie-group now',text:'🎥 Now Playing — newest releases first'});
      current.forEach(movie=>queue.push({type:'movie',movie}));
    }
    if(upcoming.length){
      queue.push({type:'heading',className:'boxoffice-movie-group upcoming',text:'🩵 Coming Soon — next releases first'});
      upcoming.forEach(movie=>queue.push({type:'movie',movie}));
    }
    if(localNews.length){
      queue.push({type:'heading',className:'boxoffice-section-title',text:`📍 ${stateName} Box Office & Theater News`});
      localNews.forEach((news,index)=>queue.push({type:'news',news,index}));
    }

    const totalCards=current.length+upcoming.length+localNews.length;
    let cursor=0;
    let renderedCards=0;
    let generation=Date.now()+Math.random();
    window.__boxOfficeRenderGeneration=generation;

    function updateCount(){
      if(!countEl)return;
      if(totalCards===0)countEl.textContent='No current Box Office cards';
      else if(renderedCards<totalCards)countEl.textContent=`Showing ${renderedCards} of ${totalCards} cards`;
      else countEl.textContent=`Showing all ${totalCards} cards`;
    }
    function appendNextBatch(limit){
      if(window.__boxOfficeRenderGeneration!==generation||active!=='boxoffice')return;
      body.querySelectorAll('.boxoffice-scroll-sentinel').forEach(el=>el.remove());
      const frag=document.createDocumentFragment();
      let added=0;
      while(cursor<queue.length&&added<limit){
        const entry=queue[cursor++];
        if(entry.type==='heading'){
          const title=document.createElement('div');title.className=entry.className;title.textContent=entry.text;frag.appendChild(title);
          continue;
        }
        if(entry.type==='movie')renderMovieCard(entry.movie,frag);
        else if(entry.type==='news')renderLocalNewsCard(entry.news,entry.index,frag);
        renderedCards+=1;
        added+=1;
      }
      body.appendChild(frag);
      updateCount();
      if(cursor>=queue.length){
        disconnectBoxOfficeObserver();
        const end=document.createElement('div');end.className='boxoffice-endcap';end.textContent='All current Box Office cards loaded';body.appendChild(end);
        return;
      }
      armObserver();
    }
    function armObserver(){
      disconnectBoxOfficeObserver();
      if(window.__boxOfficeRenderGeneration!==generation||active!=='boxoffice')return;
      const sentinel=document.createElement('div');sentinel.className='boxoffice-scroll-sentinel';sentinel.setAttribute('aria-hidden','true');body.appendChild(sentinel);
      let triggered=false;
      const observer=new IntersectionObserver(entries=>{
        if(triggered||!entries.some(entry=>entry.isIntersecting))return;
        triggered=true;
        observer.disconnect();
        window.__boxOfficeScrollObserver=null;
        requestAnimationFrame(()=>appendNextBatch(BOXOFFICE_NEXT_BATCH));
      },{root:null,rootMargin:'700px 0px 700px 0px',threshold:0.01});
      window.__boxOfficeScrollObserver=observer;
      observer.observe(sentinel);
    }

    if(!totalCards){body.insertAdjacentHTML('beforeend','<div class="empty">Movie information is temporarily unavailable.</div>');updateCount();}
    else appendNextBatch(BOXOFFICE_INITIAL_BATCH);
    sec.appendChild(body);root.appendChild(sec);
  }
  function getBoxOfficeData(){
    const now=Date.now();
    if(boxOfficeCache&&now-boxOfficeCacheAt<BOXOFFICE_CACHE_MS)return Promise.resolve(boxOfficeCache);
    if(boxOfficeRequest)return boxOfficeRequest;
    boxOfficeRequest=fetch('boxoffice.json?ts='+now,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Box Office data unavailable');return r.json()}).then(data=>{boxOfficeCache=data;boxOfficeCacheAt=Date.now();return data;}).finally(()=>{boxOfficeRequest=null;});
    return boxOfficeRequest;
  }
  function locationAwareRender(items){
    if(active!=='boxoffice')return previousRender(items);
    disconnectBoxOfficeObserver();
    const root=document.getElementById('news-feed');
    if(boxOfficeCache&&Date.now()-boxOfficeCacheAt<BOXOFFICE_CACHE_MS)renderLocalBoxOffice(boxOfficeCache);
    else root.innerHTML='<div class="loading">Loading location-specific Box Office…</div>';
    getBoxOfficeData().then(data=>{if(active==='boxoffice')renderLocalBoxOffice(data)}).catch(()=>{if(active==='boxoffice')root.innerHTML='<div class="empty">Box Office information is temporarily unavailable.</div>'});
  }
  render=locationAwareRender;
  if(previousCanonicalRender){
    canonicalRender=function(items){
      if(active==='boxoffice') return locationAwareRender(items);
      return previousCanonicalRender(items);
    };
  }
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
print('Installed canonical location-aware Box Office renderer with incremental 8-card loading, smooth append-only scrolling, local theater news continuation, release status rails, dates, showtimes, and deterministic ordering.')
