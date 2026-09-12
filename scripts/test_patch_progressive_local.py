from pathlib import Path
import re

p=Path('assets/location-content-v25.js')
s=p.read_text(encoding='utf-8')

s=s.replace("  const LOCAL_RADIUS_MILES=150;", "  const LOCAL_RADIUS_MILES=150;\n  const LOCAL_EXPANDED_RADIUS_MILES=250;\n  const LOCAL_MAX_RADIUS_MILES=400;\n  const REGION_MIN_RADIUS_MILES=400;\n  const REGION_MAX_RADIUS_MILES=800;\n  const LOCAL_MIN_STORIES=8;")

s=s.replace("  function itemRegion(item){\n    const tagged=field(item,['region']).toLowerCase();if(tagged)return tagged;\n    const code=inferredStateCode(item);return STATE_REGION[code]||'';\n  }", "  function itemRegion(item){\n    const code=inferredStateCode(item);if(code)return STATE_REGION[code]||'';\n    return field(item,['region']).toLowerCase();\n  }")

old=re.search(r"  function localPool\(items\)\{.*?\n  \}\n\n  function regionPool\(items\)\{.*?\n  \}\n", s, flags=re.S)
if not old:
    raise SystemExit('local/region pool block not found')
new="""  function localPool(items){
    const loc=location();
    const candidates=items.filter(i=>['local','region','nm','us','top'].includes(category(i)));
    if(!candidates.length||(!loc.city&&!loc.code&&loc.lat==null))return [];
    const selected=[];
    const seen=new Set();
    const add=arr=>rank(arr,loc).forEach(item=>{const k=itemKey(item);if(k&&!seen.has(k)){seen.add(k);selected.push(item)}});

    // User-city matches are strongest when the article is already local/state/regional
    // or its metadata agrees with the user's state. This avoids ambiguous organization
    // names being treated as geography merely because they equal a city name.
    add(candidates.filter(i=>matchesCity(i,loc)&&(category(i)==='local'||category(i)==='nm'||category(i)==='region'||matchesState(i,loc))));

    if(loc.lat!=null&&loc.lon!=null){
      const geotagged=candidates.map(item=>({item,d:distanceToUser(item,loc)})).filter(x=>x.d!=null).sort((a,b)=>a.d-b.d);
      const addRadius=r=>add(geotagged.filter(x=>x.d<=r).map(x=>x.item));
      addRadius(LOCAL_RADIUS_MILES);
      if(selected.length<LOCAL_MIN_STORIES)addRadius(LOCAL_EXPANDED_RADIUS_MILES);
      if(selected.length<LOCAL_MIN_STORIES)addRadius(LOCAL_MAX_RADIUS_MILES);
      if(selected.length<LOCAL_MIN_STORIES&&geotagged.length){
        const next=geotagged.find(x=>!seen.has(itemKey(x.item)));
        if(next)add(geotagged.filter(x=>x.d<=next.d+35).map(x=>x.item));
      }
    }

    if(selected.length<LOCAL_MIN_STORIES){
      const explicitLocal=candidates.filter(i=>category(i)==='local');
      add(explicitLocal.filter(i=>matchesState(i,loc)));
      if(selected.length<LOCAL_MIN_STORIES){
        // Rural fallback: accept explicit local stories only when they carry some
        // geographic evidence (state or region). Do not accept totally unlocated
        // local-tagged items, which caused false positives such as organization names.
        add(explicitLocal.filter(i=>{
          const code=inferredStateCode(i);
          const taggedRegion=field(i,['region']).toLowerCase();
          return Boolean(code||taggedRegion) && (code===loc.code||STATE_REGION[code]===loc.region||taggedRegion===loc.region);
        }));
      }
    }

    const tier=selected.length>=LOCAL_MIN_STORIES?'Local / nearest market':'Local verified';
    return selected.map(i=>cloneAs(i,'local',tier)).slice(0,90);
  }

  function regionPool(items){
    const loc=location();
    if(!loc.city&&!loc.code&&loc.lat==null)return [];
    const candidates=items.filter(i=>['region','local','nm','us','top'].includes(category(i)));

    if(loc.lat!=null&&loc.lon!=null){
      const geotagged=candidates.map(item=>({item,d:distanceToUser(item,loc)})).filter(x=>x.d!=null);
      const band=geotagged.filter(x=>x.d>REGION_MIN_RADIUS_MILES&&x.d<=REGION_MAX_RADIUS_MILES).map(x=>x.item);
      if(band.length)return rank(band,loc).map(i=>cloneAs(i,'region',`${REGION_MIN_RADIUS_MILES}-${REGION_MAX_RADIUS_MILES} miles`)).slice(0,90);
    }

    // Current feed does not consistently carry article coordinates. Until collection
    // enrichment lands, fall back only to records that the collector explicitly marked
    // as regional. This is safer than promoting arbitrary U.S./Top stories.
    const explicitRegional=candidates.filter(i=>category(i)==='region'&&Boolean(field(i,['region'])||inferredStateCode(i)));
    return rank(explicitRegional,loc).map(i=>cloneAs(i,'region','Regional verified')).slice(0,90);
  }
"""
s=s[:old.start()]+new+s[old.end():]

s=s.replace("  window.__locationContentV28=true;", "  window.__locationRadiusPolicyV30={local:[150,250,400],region:[400,800],minLocalStories:8};\n  window.__locationContentV28=true;\n  window.__locationContentV29=true;\n  window.__locationContentV30=true;")

p.write_text(s,encoding='utf-8')
print('Applied V30 geographic test patch: Local 150 -> 250 -> 400 with verified fallback; Region 400-800 distance-first with explicit-regional metadata fallback.')
