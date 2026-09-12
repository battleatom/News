(function(){
  'use strict';
  if(window.__locationContentV27)return;

  const LOCAL_RADIUS_MILES=150;
  const STATES={AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
  const STATE_REGION={AL:'southeast',AK:'pacific-northwest',AZ:'southwest',AR:'south',CA:'west',CO:'mountain',CT:'northeast',DE:'northeast',FL:'southeast',GA:'southeast',HI:'west',ID:'mountain',IL:'midwest',IN:'midwest',IA:'midwest',KS:'midwest',KY:'south',LA:'south',ME:'northeast',MD:'northeast',MA:'northeast',MI:'midwest',MN:'midwest',MS:'southeast',MO:'midwest',MT:'mountain',NE:'midwest',NV:'southwest',NH:'northeast',NJ:'northeast',NM:'southwest',NY:'northeast',NC:'southeast',ND:'midwest',OH:'midwest',OK:'south',OR:'pacific-northwest',PA:'northeast',RI:'northeast',SC:'southeast',SD:'midwest',TN:'southeast',TX:'south',UT:'mountain',VT:'northeast',VA:'south',WA:'pacific-northwest',WV:'south',WI:'midwest',WY:'mountain',DC:'northeast'};
  const REGION_LABELS={'southwest':'Southwest','west':'West','mountain':'Mountain','midwest':'Midwest','south':'South','northeast':'Northeast','pacific-northwest':'Pacific Northwest','southeast':'Southeast'};
  const IMPACT=[['emergency',24],['wildfire',22],['shooting',22],['killed',18],['death',14],['evacuation',18],['earthquake',20],['tornado',20],['flood',18],['drought',15],['water',10],['supreme court',18],['court',10],['law',12],['legislation',12],['election',16],['governor',10],['school',9],['hospital',10],['health',8],['layoff',12],['economy',9],['inflation',10],['crime',10],['police',9],['cyber',12],['outage',12],['breaking',12]];

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
    const lat=Number(cached?.lat),lon=Number(cached?.lon);
    return {code,name:stateName,city,region:STATE_REGION[code]||'',lat:Number.isFinite(lat)?lat:null,lon:Number.isFinite(lon)?lon:null,label};
  }

  function itemCoords(item){
    const lat=Number(field(item,['latitude','lat','locationLatitude','geoLat']));
    const lon=Number(field(item,['longitude','lon','lng','locationLongitude','geoLon']));
    return Number.isFinite(lat)&&Number.isFinite(lon)?{lat,lon}:null;
  }
  function radians(v){return v*Math.PI/180}
  function distanceMiles(a,b){
    if(!a||!b||a.lat==null||a.lon==null||b.lat==null||b.lon==null)return null;
    const dLat=radians(b.lat-a.lat),dLon=radians(b.lon-a.lon);
    const x=Math.sin(dLat/2)**2+Math.cos(radians(a.lat))*Math.cos(radians(b.lat))*Math.sin(dLon/2)**2;
    return 3958.7613*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));
  }
  function distanceToUser(item,loc){return distanceMiles(loc,itemCoords(item))}

  function itemState(item){return field(item,['state','stateCode']).toLowerCase()}
  function itemRegion(item){return field(item,['region']).toLowerCase()}
  function matchesState(item,loc){
    if(!loc.code&&!loc.name)return false;
    const tagged=itemState(item);
    if(tagged)return tagged===loc.code.toLowerCase()||tagged===loc.name.toLowerCase();
    const t=text(item);
    return Boolean(loc.name&&t.includes(loc.name.toLowerCase()));
  }
  function matchesCity(item,loc){return Boolean(loc.city&&text(item).includes(loc.city.toLowerCase()))}
  function matchesRegion(item,loc){return Boolean(loc.region&&itemRegion(item)===loc.region)}

  function importance(item,loc){
    const t=text(item);let score=0;
    IMPACT.forEach(([term,value])=>{if(t.includes(term))score+=value});
    if(loc.city&&t.includes(loc.city.toLowerCase()))score+=18;
    if(loc.name&&t.includes(loc.name.toLowerCase()))score+=9;
    const d=distanceToUser(item,loc);if(d!=null)score+=Math.max(0,30-d/8);
    const age=Math.max(0,(Date.now()-publishedMs(item))/3600000);score+=Math.max(0,18-age*.55);
    return score;
  }
  function rank(items,loc){return unique(items).sort((a,b)=>importance(b,loc)-importance(a,loc)||publishedMs(b)-publishedMs(a))}
  function cloneAs(item,cat,tier){
    const clone=item.cloneNode(true);let categoryEl=clone.querySelector('category');
    if(!categoryEl){categoryEl=clone.ownerDocument.createElement('category');clone.appendChild(categoryEl)}categoryEl.textContent=cat;
    if(tier){let tierEl=clone.querySelector('locationTier');if(!tierEl){tierEl=clone.ownerDocument.createElement('locationTier');clone.appendChild(tierEl)}tierEl.textContent=tier}
    return clone;
  }

  function statePool(items){
    const loc=location();
    if(!loc.code&&!loc.name)return [];
    const candidates=items.filter(item=>{
      const cat=category(item);
      if(cat==='nm'&&loc.code==='NM')return true;
      return ['region','local','us','top'].includes(cat)&&matchesState(item,loc);
    });
    return rank(candidates,loc).map(i=>cloneAs(i,'nm','State')).slice(0,90);
  }

  function localPool(items){
    const loc=location();
    const candidates=items.filter(i=>['local','region','nm','us','top'].includes(category(i)));
    if(!candidates.length)return [];

    if(loc.lat!=null&&loc.lon!=null){
      const geotagged=candidates.map(item=>({item,d:distanceToUser(item,loc)})).filter(x=>x.d!=null).sort((a,b)=>a.d-b.d);
      const within=geotagged.filter(x=>x.d<=LOCAL_RADIUS_MILES).map(x=>x.item);
      if(within.length)return rank(within,loc).map(i=>cloneAs(i,'local',`Within ${LOCAL_RADIUS_MILES} miles`)).slice(0,90);
      if(geotagged.length){
        const nearestDistance=geotagged[0].d;
        const nearest=geotagged.filter(x=>x.d<=nearestDistance+25).map(x=>x.item);
        return rank(nearest,loc).map(i=>cloneAs(i,'local','Nearest available')).slice(0,90);
      }
    }

    const cityMatches=candidates.filter(i=>matchesCity(i,loc));
    if(cityMatches.length)return rank(cityMatches,loc).map(i=>cloneAs(i,'local','City')).slice(0,90);
    const stateMatches=candidates.filter(i=>matchesState(i,loc));
    if(stateMatches.length)return rank(stateMatches,loc).map(i=>cloneAs(i,'local','Closest available in state')).slice(0,90);
    const regionMatches=candidates.filter(i=>matchesRegion(i,loc));
    return rank(regionMatches,loc).map(i=>cloneAs(i,'local','Closest available in region')).slice(0,90);
  }

  function regionPool(items){
    const loc=location();
    if(!loc.region)return [];
    return rank(items.filter(i=>category(i)==='region'&&matchesRegion(i,loc)),loc).map(i=>cloneAs(i,'region','Regional')).slice(0,90);
  }

  function updateLabels(){
    if(typeof CANONICAL_SECTIONS==='undefined'||!Array.isArray(CANONICAL_SECTIONS))return;
    const loc=location();
    const state=CANONICAL_SECTIONS.find(x=>x[0]==='nm');
    const local=CANONICAL_SECTIONS.find(x=>x[0]==='local');
    const region=CANONICAL_SECTIONS.find(x=>x[0]==='region');
    if(state)state[1]=loc.name?`🗺️ ${loc.name}`:'🗺️ State';
    if(local)local[1]=loc.city?`📍 Local · ${loc.city}`:'📍 Local';
    if(region)region[1]=loc.region?`🌎 ${REGION_LABELS[loc.region]||loc.region}`:'🌎 Region';
    if(typeof sections!=='undefined')sections=CANONICAL_SECTIONS;
  }

  const basePaginated=typeof paginatedNewsItems==='function'?paginatedNewsItems:null;
  if(basePaginated){
    const v27=function(items){
      if(active==='nm')return basePaginated(statePool(items));
      if(active==='local')return basePaginated(localPool(items));
      if(active==='region')return basePaginated(regionPool(items));
      return basePaginated(items);
    };
    paginatedNewsItems=v27;window.paginatedNewsItems=v27;
  }

  function refreshLocationView(){
    updateLabels();
    if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();
    if(typeof active!=='undefined'&&['nm','local','region'].includes(active)&&typeof canonicalRender==='function'&&typeof allItems!=='undefined')canonicalRender(allItems);
  }

  window.__locationStatePoolV27=statePool;
  window.__locationLocalPoolV27=localPool;
  window.__locationRegionPoolV27=regionPool;
  window.__locationDistanceMilesV27=distanceMiles;
  window.__locationRadiusMilesV27=LOCAL_RADIUS_MILES;
  window.addEventListener('underreported:location',refreshLocationView);
  updateLabels();
  if(window.UnderreportedLocation?.get)window.UnderreportedLocation.get().then(refreshLocationView).catch(()=>refreshLocationView());
  window.__locationContentV25=true;
  window.__locationContentV26=true;
  window.__locationContentV27=true;
})();
