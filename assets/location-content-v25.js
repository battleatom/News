(function(){
  'use strict';
  if(window.__locationContentV25)return;
  const STATES={AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
  const FEDERAL_TERMS=['congress','senate','house of representatives','capitol hill','supreme court','scotus','department of justice','justice department',' doj ','fbi','homeland security',' dhs ','treasury department','u.s. treasury','state department','federal reserve','ftc','fcc','sec ','epa','irs','fema','cdc','hhs','federal judge','federal court','federal appeals','federal agency','federal government','pentagon'];
  const FOUR_CORNERS_CITIES=['farmington','aztec','bloomfield','kirtland','shiprock'];

  function category(item){return (item.querySelector('category')?.textContent||'').trim()}
  function text(item){return `${item.querySelector('title')?.textContent||''} ${item.querySelector('description')?.textContent||''} ${item.querySelector('source')?.textContent||''}`.toLowerCase()}
  function itemKey(item){
    if(typeof normalizeDuplicateKey==='function')return normalizeDuplicateKey(item);
    return (item.querySelector('link')?.textContent||item.querySelector('title')?.textContent||'').trim().toLowerCase();
  }
  function newest(items){return [...items].sort((a,b)=>(Date.parse(b.querySelector('pubDate')?.textContent||'')||0)-(Date.parse(a.querySelector('pubDate')?.textContent||'')||0))}
  function unique(items){const seen=new Set();return newest(items).filter(item=>{const k=itemKey(item);if(!k||seen.has(k))return false;seen.add(k);return true})}
  function cloneAs(item,newCategory){
    const clone=item.cloneNode(true);let cat=clone.querySelector('category');
    if(!cat){cat=clone.ownerDocument.createElement('category');clone.appendChild(cat)}cat.textContent=newCategory;return clone;
  }
  function location(){
    let cached=null;try{cached=window.UnderreportedLocation?.cached?.()||null}catch(e){}
    let code=String(cached?.state||localStorage.getItem('underreported-state')||'NM').replace(/^US-/,'').toUpperCase();
    if(!STATES[code])code='NM';
    const label=String(cached?.label||localStorage.getItem('underreported-location')||'');
    const city=String(cached?.city||label.split(',')[0]||'').trim();
    return {code,name:STATES[code],city};
  }
  function matchesState(item,loc){
    const tagged=(item.querySelector('state')?.textContent||'').trim().toLowerCase();
    if(tagged)return tagged===loc.name.toLowerCase()||tagged===loc.code.toLowerCase();
    return text(item).includes(loc.name.toLowerCase());
  }
  function statePool(items){
    const loc=location(), out=[];
    if(loc.code==='NM')out.push(...items.filter(i=>category(i)==='nm'));
    out.push(...items.filter(i=>category(i)==='region'&&matchesState(i,loc)));
    out.push(...items.filter(i=>['us','top'].includes(category(i))&&matchesState(i,loc)));
    return unique(out).slice(0,30);
  }
  function localPool(items){
    const loc=location(), city=loc.city.toLowerCase(), exact=[];
    if(loc.code==='NM')exact.push(...items.filter(i=>category(i)==='local'&&(!city||text(i).includes(city)||FOUR_CORNERS_CITIES.includes(city))));
    const state=statePool(items);
    if(city)exact.push(...state.filter(i=>text(i).includes(city)));
    let pool=unique(exact);
    if(pool.length<10)pool=unique(pool.concat(state)).slice(0,30);
    return pool;
  }
  function federalPool(items){
    const direct=items.filter(i=>category(i)==='federal');
    const extra=items.filter(i=>['us','top','presidential','legislation'].includes(category(i))&&FEDERAL_TERMS.some(term=>` ${text(i)} `.includes(term)));
    return unique(direct.concat(extra)).slice(0,30);
  }
  function updateLabels(){
    const loc=location();
    const stateDef=typeof CANONICAL_SECTIONS!=='undefined'?CANONICAL_SECTIONS.find(x=>x[0]==='nm'):null;
    const localDef=typeof CANONICAL_SECTIONS!=='undefined'?CANONICAL_SECTIONS.find(x=>x[0]==='local'):null;
    const cityKey=loc.city.toLowerCase();
    const localName=loc.code==='NM'&&FOUR_CORNERS_CITIES.includes(cityKey)?'Four Corners':(loc.city||loc.name);
    if(stateDef)stateDef[1]=`🗺️ ${loc.name}`;
    if(localDef)localDef[1]=`📍 Local / ${localName}`;
  }

  const basePaginated=typeof paginatedNewsItems==='function'?paginatedNewsItems:null;
  if(basePaginated){
    const v25=function(items){
      if(active==='federal')return basePaginated(federalPool(items).map(i=>cloneAs(i,'federal')));
      if(active==='nm')return basePaginated(statePool(items).map(i=>cloneAs(i,'nm')));
      if(active==='local')return basePaginated(localPool(items).map(i=>cloneAs(i,'local')));
      return basePaginated(items);
    };
    paginatedNewsItems=v25;window.paginatedNewsItems=v25;
  }

  function refreshLocationView(){
    updateLabels();
    if(typeof loadCounts!=='undefined'){loadCounts.nm=10;loadCounts.local=10;loadCounts.legislation=10;}
    if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();
    if(typeof active!=='undefined'&&['nm','local','legislation'].includes(active)&&typeof canonicalRender==='function'&&typeof allItems!=='undefined')canonicalRender(allItems);
  }
  window.addEventListener('underreported:location',refreshLocationView);
  updateLabels();
  if(window.UnderreportedLocation?.get)window.UnderreportedLocation.get().then(refreshLocationView).catch(()=>refreshLocationView());
  window.__locationContentV25=true;
})();
