(function(){
  'use strict';
  if(window.__locationContentV26)return;
  const STATES={AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
  const STATE_REGION={AL:'southeast',AK:'pacific-northwest',AZ:'southwest',AR:'south',CA:'west',CO:'mountain',CT:'northeast',DE:'northeast',FL:'southeast',GA:'southeast',HI:'west',ID:'mountain',IL:'midwest',IN:'midwest',IA:'midwest',KS:'midwest',KY:'south',LA:'south',ME:'northeast',MD:'northeast',MA:'northeast',MI:'midwest',MN:'midwest',MS:'southeast',MO:'midwest',MT:'mountain',NE:'midwest',NV:'southwest',NH:'northeast',NJ:'northeast',NM:'southwest',NY:'northeast',NC:'southeast',ND:'midwest',OH:'midwest',OK:'south',OR:'pacific-northwest',PA:'northeast',RI:'northeast',SC:'southeast',SD:'midwest',TN:'southeast',TX:'south',UT:'mountain',VT:'northeast',VA:'south',WA:'pacific-northwest',WV:'south',WI:'midwest',WY:'mountain',DC:'northeast'};
  const FEDERAL_TERMS=['congress','senate','house of representatives','capitol hill','supreme court','scotus','department of justice','justice department',' doj ','fbi','homeland security',' dhs ','treasury department','u.s. treasury','state department','federal reserve','ftc','fcc','sec ','epa','irs','fema','cdc','hhs','federal judge','federal court','federal appeals','federal agency','federal government','pentagon'];
  const PRESIDENTIAL_DIRECT=['donald trump','president trump','trump ',' trump','white house','u.s. president','us president','president of the united states','oval office','trump administration','vice president vance','jd vance','j.d. vance','karoline leavitt','white house press secretary'];
  const PRESIDENTIAL_ACTION=['executive order','presidential action','presidential memorandum','presidential proclamation','cabinet meeting','administration official'];
  const FOUR_CORNERS_CITIES=['farmington','aztec','bloomfield','kirtland','shiprock'];
  const FOUR_CORNERS_LOCAL_TERMS=['farmington','san juan county','aztec','bloomfield','kirtland','shiprock','four corners'];
  const IMPACT=[['emergency',24],['wildfire',22],['shooting',22],['killed',18],['death',14],['evacuation',18],['earthquake',20],['tornado',20],['flood',18],['drought',15],['water',10],['supreme court',18],['court',10],['law',12],['legislation',12],['election',16],['governor',10],['school',9],['hospital',10],['health',8],['layoff',12],['economy',9],['inflation',10],['crime',10],['police',9],['cyber',12],['outage',12],['breaking',12]];
  const EVENT_STOP=new Set(['this','that','with','from','have','will','after','into','over','about','amid','says','said','news','new','more','than','their','there','where','what','when','your','they','them','been','were','would','could','should','state','local','mexico']);

  function category(item){return (item.querySelector('category')?.textContent||'').trim()}
  function text(item){return `${item.querySelector('title')?.textContent||''} ${item.querySelector('description')?.textContent||''} ${item.querySelector('source')?.textContent||''}`.toLowerCase()}
  function itemKey(item){
    if(typeof normalizeDuplicateKey==='function')return normalizeDuplicateKey(item);
    return (item.querySelector('link')?.textContent||item.querySelector('title')?.textContent||'').trim().toLowerCase();
  }
  function titleWords(item){
    const raw=(item.querySelector('title')?.textContent||'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ');
    return [...new Set(raw.split(/\s+/).filter(w=>w.length>=4&&!EVENT_STOP.has(w)))];
  }
  function sameStateEvent(a,b){
    if(itemKey(a)===itemKey(b))return true;
    const aw=titleWords(a),bw=titleWords(b);if(!aw.length||!bw.length)return false;
    const bs=new Set(bw),common=aw.filter(w=>bs.has(w)).length;
    const denom=Math.min(aw.length,bw.length);
    return denom>=3&&common>=3&&common/denom>=0.6;
  }
  function stateUnique(items){
    const out=[];
    for(const item of items){if(out.some(existing=>sameStateEvent(existing,item)))continue;out.push(item)}
    return out;
  }
  function publishedMs(item){return Date.parse(item.querySelector('pubDate')?.textContent||'')||0}
  function unique(items){const seen=new Set();return items.filter(item=>{const k=itemKey(item);if(!k||seen.has(k))return false;seen.add(k);return true})}
  function location(){
    let cached=null;try{cached=window.UnderreportedLocation?.cached?.()||null}catch(e){}
    let code=String(cached?.state||localStorage.getItem('underreported-state')||'NM').replace(/^US-/,'').toUpperCase();
    if(!STATES[code])code='NM';
    const label=String(cached?.label||localStorage.getItem('underreported-location')||'');
    const city=String(cached?.city||label.split(',')[0]||'').trim();
    return {code,name:STATES[code],city,region:STATE_REGION[code]||'southwest'};
  }
  function matchesState(item,loc){
    const tagged=(item.querySelector('state')?.textContent||'').trim().toLowerCase();
    if(tagged)return tagged===loc.name.toLowerCase()||tagged===loc.code.toLowerCase();
    return text(item).includes(loc.name.toLowerCase());
  }
  function matchesCity(item,loc){
    if(!loc.city)return false;
    const t=text(item),city=loc.city.toLowerCase();
    if(t.includes(city))return true;
    if(loc.code==='NM'&&FOUR_CORNERS_CITIES.includes(city))return FOUR_CORNERS_LOCAL_TERMS.some(term=>t.includes(term));
    return false;
  }
  function importance(item,loc){
    const t=text(item);let score=0;
    IMPACT.forEach(([term,value])=>{if(t.includes(term))score+=value});
    if(t.includes(loc.city.toLowerCase())&&loc.city)score+=18;
    if(t.includes(loc.name.toLowerCase()))score+=9;
    const age=Math.max(0,(Date.now()-publishedMs(item))/3600000);score+=Math.max(0,18-age*.55);
    return score;
  }
  function rank(items,loc){return unique(items).sort((a,b)=>importance(b,loc)-importance(a,loc)||publishedMs(b)-publishedMs(a))}
  function addTier(item,tier){
    const clone=item.cloneNode(true);let cat=clone.querySelector('category');
    if(!cat){cat=clone.ownerDocument.createElement('category');clone.appendChild(cat)}cat.textContent='nm';
    let tierEl=clone.querySelector('locationTier');if(!tierEl){tierEl=clone.ownerDocument.createElement('locationTier');clone.appendChild(tierEl)}tierEl.textContent=tier;
    return clone;
  }
  function take(items,count,used,chosen=[]){const out=[];for(const item of items){const k=itemKey(item);if(!k||used.has(k)||chosen.concat(out).some(existing=>sameStateEvent(existing,item)))continue;used.add(k);out.push(item);if(out.length>=count)break}return out}

  function presidentialRelevant(item){
    const t=` ${text(item)} `;
    if(PRESIDENTIAL_DIRECT.some(term=>t.includes(term)))return true;
    const usContext=t.includes('united states')||t.includes('u.s.')||t.includes('american');
    return usContext&&PRESIDENTIAL_ACTION.some(term=>t.includes(term));
  }
  function presidentialPool(items){return rank(items.filter(i=>category(i)==='presidential'&&presidentialRelevant(i)),location()).slice(0,30)}

  function federalPool(items){
    const direct=items.filter(i=>category(i)==='federal');
    const extra=items.filter(i=>['us','top','presidential','legislation'].includes(category(i))&&FEDERAL_TERMS.some(term=>` ${text(i)} `.includes(term)));
    return rank(direct.concat(extra),location()).slice(0,30);
  }

  function mergedStatePool(items){
    const loc=location();
    const stateSpecific=[];
    if(loc.code==='NM')stateSpecific.push(...items.filter(i=>category(i)==='nm'));
    stateSpecific.push(...items.filter(i=>category(i)==='region'&&matchesState(i,loc)));
    stateSpecific.push(...items.filter(i=>['us','top'].includes(category(i))&&matchesState(i,loc)));

    const regional=items.filter(i=>category(i)==='region'&&((i.querySelector('region')?.textContent||'').trim()===loc.region));
    let local=items.filter(i=>category(i)==='local'&&matchesCity(i,loc));
    local=local.concat(items.filter(i=>['region','us','top','nm'].includes(category(i))&&matchesCity(i,loc)));

    const localRanked=stateUnique(rank(local,loc)),stateRanked=stateUnique(rank(stateSpecific,loc)),regionalRanked=stateUnique(rank(regional,loc));
    const used=new Set();
    const topState=take(stateRanked,6,used);
    const topRegional=take(regionalRanked,6,used,topState);
    const topLocal=take(localRanked,6,used,topState.concat(topRegional));
    const selected=topState.concat(topRegional,topLocal);
    const top=[...topState.map(i=>addTier(i,'State')),...topRegional.map(i=>addTier(i,'Regional')),...topLocal.map(i=>addTier(i,'Local'))];
    const remainder=stateUnique(rank([...stateRanked,...regionalRanked,...localRanked],loc)).filter(i=>!used.has(itemKey(i))&&!selected.some(existing=>sameStateEvent(existing,i))).map(i=>addTier(i,'Ranked'));
    window.__stateMergeCountsV26={state:topState.length,regional:topRegional.length,local:topLocal.length,total:top.length+remainder.length,location:loc};
    return stateUnique([...top,...remainder]).slice(0,90);
  }

  function removeMergedTabs(){
    if(typeof CANONICAL_SECTIONS==='undefined'||!Array.isArray(CANONICAL_SECTIONS))return;
    for(let i=CANONICAL_SECTIONS.length-1;i>=0;i--){if(['local','region'].includes(CANONICAL_SECTIONS[i]?.[0]))CANONICAL_SECTIONS.splice(i,1)}
    if(typeof sections!=='undefined')sections=CANONICAL_SECTIONS;
    try{
      if(typeof active!=='undefined'&&['local','region'].includes(active)){active='nm';localStorage.setItem('underreported-active-tab','nm')}
    }catch(e){}
  }
  function updateLabel(){
    const loc=location();
    const def=typeof CANONICAL_SECTIONS!=='undefined'?CANONICAL_SECTIONS.find(x=>x[0]==='nm'):null;
    if(def)def[1]=`🗺️ ${loc.name}`;
  }

  const basePaginated=typeof paginatedNewsItems==='function'?paginatedNewsItems:null;
  if(basePaginated){
    const v26=function(items){
      if(active==='presidential')return basePaginated(presidentialPool(items).map(i=>{const c=i.cloneNode(true);return c}));
      if(active==='federal')return basePaginated(federalPool(items).map(i=>{const c=i.cloneNode(true);let cat=c.querySelector('category');if(cat)cat.textContent='federal';return c}));
      if(active==='nm')return basePaginated(mergedStatePool(items));
      return basePaginated(items);
    };
    paginatedNewsItems=v26;window.paginatedNewsItems=v26;
  }

  function refreshLocationView(){
    removeMergedTabs();updateLabel();
    if(typeof loadCounts!=='undefined'){loadCounts.nm=10;loadCounts.legislation=10;}
    if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();
    if(typeof active!=='undefined'&&['nm','legislation'].includes(active)&&typeof canonicalRender==='function'&&typeof allItems!=='undefined')canonicalRender(allItems);
  }
  window.__presidentialRelevantV26=presidentialRelevant;
  window.__sameStateEventV281=sameStateEvent;
  window.__mergedStatePoolV26=mergedStatePool;
  window.addEventListener('underreported:location',refreshLocationView);
  removeMergedTabs();updateLabel();
  if(window.UnderreportedLocation?.get)window.UnderreportedLocation.get().then(refreshLocationView).catch(()=>refreshLocationView());
  window.__locationContentV25=true;
  window.__locationContentV26=true;
  window.__locationDedupeV281=true;
})();
