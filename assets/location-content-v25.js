(function(){
  'use strict';
  if(window.__locationContentV34)return;

  const LOCAL_RADIUS_MILES=150;
  const LOCAL_MIN_STORIES=8;
  const LOCAL_MAX_MARKETS=3;
  const STATES={AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
  const STATE_REGION={AL:'southeast',AK:'pacific-northwest',AZ:'southwest',AR:'south',CA:'west',CO:'mountain',CT:'northeast',DE:'northeast',FL:'southeast',GA:'southeast',HI:'west',ID:'mountain',IL:'midwest',IN:'midwest',IA:'midwest',KS:'midwest',KY:'south',LA:'south',ME:'northeast',MD:'northeast',MA:'northeast',MI:'midwest',MN:'midwest',MS:'southeast',MO:'midwest',MT:'mountain',NE:'midwest',NV:'southwest',NH:'northeast',NJ:'northeast',NM:'southwest',NY:'northeast',NC:'southeast',ND:'midwest',OH:'midwest',OK:'south',OR:'pacific-northwest',PA:'northeast',RI:'northeast',SC:'southeast',SD:'midwest',TN:'southeast',TX:'south',UT:'mountain',VT:'northeast',VA:'south',WA:'pacific-northwest',WV:'south',WI:'midwest',WY:'mountain',DC:'northeast'};
  const REGION_LABELS={'southwest':'Southwest','west':'West','mountain':'Mountain','midwest':'Midwest','south':'South','northeast':'Northeast','pacific-northwest':'Pacific Northwest','southeast':'Southeast'};
  const IMPACT=[['emergency',24],['wildfire',22],['shooting',22],['killed',18],['death',14],['evacuation',18],['earthquake',20],['tornado',20],['flood',18],['drought',15],['water',10],['supreme court',18],['court',10],['law',12],['legislation',12],['election',16],['governor',10],['school',9],['hospital',10],['health',8],['layoff',12],['economy',9],['inflation',10],['crime',10],['police',9],['cyber',12],['outage',12],['breaking',12]];

  let NEWS_MARKETS=[];
  let MARKET_BY_ID={};
  let SOURCE_MARKET={};

  function normalizeSource(v){return String(v||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}
  async function loadMarketDatabase(){
    try{
      const manifest=await fetch('data/us_news_markets.json?v=1',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`market manifest ${r.status}`);return r.json()});
      const parts=await Promise.all((manifest.files||[]).map(path=>fetch(`data/${path}?v=1`,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`market data ${r.status}`);return r.json()})));
      NEWS_MARKETS=parts.flatMap(x=>x.markets||[]);
      MARKET_BY_ID=Object.fromEntries(NEWS_MARKETS.map(m=>[m.id,m]));
      SOURCE_MARKET={};
      NEWS_MARKETS.forEach(m=>(m.sources||[]).forEach(src=>{SOURCE_MARKET[normalizeSource(src)]=m.id}));
      window.UnderreportedNewsMarkets={version:manifest.version||1,markets:NEWS_MARKETS,byId:MARKET_BY_ID,sourceMap:SOURCE_MARKET};
      refreshLocationView();
    }catch(err){console.warn('News market database unavailable; using feed metadata only.',err)}
  }

  function category(item){return (item.querySelector('category')?.textContent||'').trim().toLowerCase()}
  function text(item){return `${item.querySelector('title')?.textContent||''} ${item.querySelector('description')?.textContent||''} ${item.querySelector('source')?.textContent||''}`.toLowerCase()}
  function field(item,names){for(const name of names){const value=item.querySelector(name)?.textContent?.trim();if(value)return value}return ''}
  function itemKey(item){if(typeof normalizeDuplicateKey==='function')return normalizeDuplicateKey(item);return (item.querySelector('link')?.textContent||item.querySelector('guid')?.textContent||item.querySelector('title')?.textContent||'').trim().toLowerCase()}
  function publishedMs(item){return Date.parse(item.querySelector('pubDate')?.textContent||'')||0}
  function unique(items){const seen=new Set();return items.filter(item=>{const k=itemKey(item);if(!k||seen.has(k))return false;seen.add(k);return true})}

  function location(){
    let cached=null;try{cached=window.UnderreportedLocation?.cached?.()||null}catch(e){}
    const code=String(cached?.state||localStorage.getItem('underreported-state')||'').replace(/^US-/,'').toUpperCase();
    const stateName=STATES[code]||'';
    const label=String(cached?.label||localStorage.getItem('underreported-location')||'');
    const city=String(cached?.city||label.split(',')[0]||'').trim();
    const rawLat=cached?.lat,rawLon=cached?.lon;
    const lat=rawLat==null||rawLat===''?null:Number(rawLat),lon=rawLon==null||rawLon===''?null:Number(rawLon);
    return {code,name:stateName,city,region:STATE_REGION[code]||'',lat:Number.isFinite(lat)?lat:null,lon:Number.isFinite(lon)?lon:null,label};
  }

  function numericField(item,names){const raw=field(item,names);if(raw==='')return null;const n=Number(raw);return Number.isFinite(n)?n:null}
  function itemCoords(item){const lat=numericField(item,['latitude','lat','locationLatitude','geoLat']);const lon=numericField(item,['longitude','lon','lng','locationLongitude','geoLon']);return lat!=null&&lon!=null?{lat,lon}:null}
  function radians(v){return v*Math.PI/180}
  function distanceMiles(a,b){if(!a||!b||a.lat==null||a.lon==null||b.lat==null||b.lon==null)return null;const dLat=radians(b.lat-a.lat),dLon=radians(b.lon-a.lon);const x=Math.sin(dLat/2)**2+Math.cos(radians(a.lat))*Math.cos(radians(b.lat))*Math.sin(dLon/2)**2;return 3958.7613*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x))}
  function distanceToUser(item,loc){return distanceMiles(loc,itemCoords(item))}

  function normalizedStateCode(value){const raw=String(value||'').trim();if(!raw)return '';const upper=raw.replace(/^US-/i,'').toUpperCase();if(STATES[upper])return upper;const hit=Object.entries(STATES).find(([,name])=>name.toLowerCase()===raw.toLowerCase());return hit?hit[0]:''}
  function itemStateCode(item){return normalizedStateCode(field(item,['marketState','state','stateCode']))}
  function inferredStateCode(item){const tagged=itemStateCode(item);if(tagged)return tagged;const t=` ${text(item)} `;for(const [code,name] of Object.entries(STATES)){if(t.includes(` ${name.toLowerCase()} `))return code}return ''}
  function itemRegion(item){const code=inferredStateCode(item);if(code)return STATE_REGION[code]||'';return field(item,['region']).toLowerCase()}
  function matchesState(item,loc){if(!loc.code&&!loc.name)return false;const code=inferredStateCode(item);if(code)return code===loc.code;return Boolean(loc.name&&text(item).includes(loc.name.toLowerCase()))}
  function matchesCity(item,loc){return Boolean(loc.city&&text(item).includes(loc.city.toLowerCase()))}
  function matchesRegion(item,loc){return Boolean(loc.region&&itemRegion(item)===loc.region)}

  function sourceMarket(item){
    const explicit=field(item,['marketId']);if(explicit&&MARKET_BY_ID[explicit])return MARKET_BY_ID[explicit];
    const coords=itemCoords(item);if(explicit&&coords)return {id:explicit,city:field(item,['marketCity']),state:field(item,['marketState']),lat:coords.lat,lon:coords.lon,region:itemRegion(item)};
    const src=normalizeSource(field(item,['source']));const id=SOURCE_MARKET[src];return id?MARKET_BY_ID[id]:null;
  }
  function marketGroups(items,loc){
    const groups=new Map();
    items.forEach(item=>{const market=sourceMarket(item);if(!market)return;if(!groups.has(market.id))groups.set(market.id,{market,items:[]});groups.get(market.id).items.push(item)});
    return [...groups.values()].map(g=>({...g,d:distanceMiles(loc,g.market)})).filter(g=>g.d!=null).sort((a,b)=>a.d-b.d);
  }

  function importance(item,loc){const t=text(item);let score=0;IMPACT.forEach(([term,value])=>{if(t.includes(term))score+=value});if(loc.city&&t.includes(loc.city.toLowerCase()))score+=18;if(loc.name&&t.includes(loc.name.toLowerCase()))score+=9;const d=distanceToUser(item,loc);if(d!=null)score+=Math.max(0,30-d/8);const age=Math.max(0,(Date.now()-publishedMs(item))/3600000);score+=Math.max(0,18-age*.55);return score}
  function rank(items,loc){return unique(items).sort((a,b)=>importance(b,loc)-importance(a,loc)||publishedMs(b)-publishedMs(a))}
  function cloneAs(item,cat,tier){const clone=item.cloneNode(true);let categoryEl=clone.querySelector('category');if(!categoryEl){categoryEl=clone.ownerDocument.createElement('category');clone.appendChild(categoryEl)}categoryEl.textContent=cat;if(tier){let tierEl=clone.querySelector('locationTier');if(!tierEl){tierEl=clone.ownerDocument.createElement('locationTier');clone.appendChild(tierEl)}tierEl.textContent=tier}return clone}

  function statePool(items){const loc=location();if(!loc.code&&!loc.name)return [];const candidates=items.filter(item=>{const cat=category(item);if(cat==='nm'&&loc.code==='NM')return true;return ['region','local','us','top'].includes(cat)&&matchesState(item,loc)});return rank(candidates,loc).map(i=>cloneAs(i,'nm','State')).slice(0,90)}

  function nearestLocalSelection(items,loc){
    const candidates=items.filter(i=>['local','region','nm','us','top'].includes(category(i)));
    const selected=[];const seen=new Set();const usedMarkets=[];
    const add=arr=>rank(arr,loc).forEach(item=>{const k=itemKey(item);if(k&&!seen.has(k)){seen.add(k);selected.push(item)}});
    add(candidates.filter(i=>matchesCity(i,loc)&&matchesState(i,loc)));
    for(const group of marketGroups(candidates.filter(i=>category(i)==='local'),loc)){
      if(selected.length>=LOCAL_MIN_STORIES||usedMarkets.length>=LOCAL_MAX_MARKETS)break;
      add(group.items);usedMarkets.push(group.market.id);
    }
    if(selected.length<LOCAL_MIN_STORIES&&loc.lat!=null&&loc.lon!=null){
      const geotagged=candidates.map(item=>({item,d:distanceToUser(item,loc)})).filter(x=>x.d!=null&&x.d<=LOCAL_RADIUS_MILES).sort((a,b)=>a.d-b.d);
      add(geotagged.map(x=>x.item));
    }
    if(selected.length<LOCAL_MIN_STORIES)add(candidates.filter(i=>category(i)==='local'&&matchesState(i,loc)));
    return {selected,usedMarkets};
  }

  function localPool(items){const loc=location();if(!loc.city&&!loc.code&&loc.lat==null)return [];const result=nearestLocalSelection(items,loc);return result.selected.map(i=>cloneAs(i,'local','Nearest active news market')).slice(0,90)}

  function regionPool(items){
    const loc=location();if(!loc.city&&!loc.code&&loc.lat==null)return [];
    const candidates=items.filter(i=>['region','local','nm'].includes(category(i)));
    const withMarkets=[];const withoutMarkets=[];
    candidates.forEach(item=>{const m=sourceMarket(item);if(m){const d=distanceMiles(loc,m);withMarkets.push({item,d:d==null?Number.MAX_SAFE_INTEGER:d})}else withoutMarkets.push(item)});
    withMarkets.sort((a,b)=>a.d-b.d);
    const ordered=withMarkets.map(x=>x.item).concat(rank(withoutMarkets.filter(i=>category(i)==='region'&&(matchesRegion(i,loc)||!field(i,['region']))),loc));
    return unique(ordered).map(i=>cloneAs(i,'region','Nearest regional markets')).slice(0,90);
  }

  function updateLabels(){if(typeof CANONICAL_SECTIONS==='undefined'||!Array.isArray(CANONICAL_SECTIONS))return;const loc=location();const state=CANONICAL_SECTIONS.find(x=>x[0]==='nm');const local=CANONICAL_SECTIONS.find(x=>x[0]==='local');const region=CANONICAL_SECTIONS.find(x=>x[0]==='region');if(state)state[1]=loc.name?`🗺️ ${loc.name}`:'🗺️ State';if(local)local[1]=loc.city?`📍 Local · ${loc.city}`:'📍 Local';if(region)region[1]=loc.region?`🌎 ${REGION_LABELS[loc.region]||loc.region}`:'🌎 Region';if(typeof sections!=='undefined')sections=CANONICAL_SECTIONS}

  const basePaginated=typeof paginatedNewsItems==='function'?paginatedNewsItems:null;
  if(basePaginated){const v34=function(items){if(active==='nm')return basePaginated(statePool(items));if(active==='local')return basePaginated(localPool(items));if(active==='region')return basePaginated(regionPool(items));return basePaginated(items)};paginatedNewsItems=v34;window.paginatedNewsItems=v34}

  function refreshLocationView(){updateLabels();if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();if(typeof active!=='undefined'&&['nm','local','region'].includes(active)&&typeof canonicalRender==='function'&&typeof allItems!=='undefined')canonicalRender(allItems)}

  window.__locationStatePoolV27=statePool;window.__locationLocalPoolV27=localPool;window.__locationRegionPoolV27=regionPool;window.__locationDistanceMilesV27=distanceMiles;window.__locationRadiusMilesV27=LOCAL_RADIUS_MILES;
  window.__locationStatePoolV28=statePool;window.__locationLocalPoolV28=localPool;window.__locationRegionPoolV28=regionPool;
  window.__locationMarketPolicyV34={minLocalStories:LOCAL_MIN_STORIES,maxLocalMarkets:LOCAL_MAX_MARKETS,database:'data/us_news_markets.json'};
  window.addEventListener('underreported:location',refreshLocationView);
  updateLabels();
  loadMarketDatabase();
  if(window.UnderreportedLocation?.get)window.UnderreportedLocation.get().then(refreshLocationView).catch(()=>refreshLocationView());
  window.__locationContentV25=true;window.__locationContentV26=true;window.__locationContentV27=true;window.__locationContentV28=true;window.__locationContentV29=true;window.__locationContentV30=true;window.__locationContentV31=true;window.__locationContentV32=true;window.__locationContentV33=true;window.__locationContentV34=true;
})();
