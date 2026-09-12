from pathlib import Path
import re

p=Path('assets/location-content-v25.js')
s=p.read_text(encoding='utf-8')

s=s.replace("  const LOCAL_RADIUS_MILES=150;", "  const LOCAL_RADIUS_MILES=150;\n  const LOCAL_EXPANDED_RADIUS_MILES=250;\n  const LOCAL_MAX_RADIUS_MILES=400;\n  const LOCAL_MIN_STORIES=8;")

s=s.replace("  function itemRegion(item){\n    const tagged=field(item,['region']).toLowerCase();if(tagged)return tagged;\n    const code=inferredStateCode(item);return STATE_REGION[code]||'';\n  }", "  function itemRegion(item){\n    const code=inferredStateCode(item);if(code)return STATE_REGION[code]||'';\n    return field(item,['region']).toLowerCase();\n  }")

old=re.search(r"  function localPool\(items\)\{.*?\n  \}\n\n  function regionPool", s, flags=re.S)
if not old:
    raise SystemExit('localPool block not found')
new="""  function localPool(items){
    const loc=location();
    const candidates=items.filter(i=>['local','region','nm','us','top'].includes(category(i)));
    if(!candidates.length||(!loc.city&&!loc.code&&loc.lat==null))return [];
    const selected=[];
    const seen=new Set();
    const add=arr=>rank(arr,loc).forEach(item=>{const k=itemKey(item);if(k&&!seen.has(k)){seen.add(k);selected.push(item)}});

    add(candidates.filter(i=>matchesCity(i,loc)));

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
        add(explicitLocal.filter(i=>{
          const code=inferredStateCode(i);
          return !code||code===loc.code||STATE_REGION[code]===loc.region;
        }));
      }
    }

    const tier=selected.length>=LOCAL_MIN_STORIES?'Local / nearest market':'Local verified';
    return selected.map(i=>cloneAs(i,'local',tier)).slice(0,90);
  }

  function regionPool"""
s=s[:old.start()]+new+s[old.end():]

s=s.replace("  window.__locationContentV28=true;", "  window.__locationRadiusPolicyV29={primary:150,expanded:250,max:400,minStories:8};\n  window.__locationContentV28=true;\n  window.__locationContentV29=true;")

p.write_text(s,encoding='utf-8')
print('Applied progressive Local test patch: 150 -> 250 -> 400 -> nearest verified market, min 8 stories.')
