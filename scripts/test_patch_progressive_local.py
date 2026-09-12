from pathlib import Path
import re

p=Path('assets/location-content-v25.js')
s=p.read_text(encoding='utf-8')

# V32 test: use active publisher markets instead of requiring every article to carry coordinates.
# The routing algorithm is generic; this registry is separate data that can be expanded nationwide
# without changing Local/Region selection logic.
market_js="""
  const NEWS_MARKETS={
    'tri city record':{id:'farmington-nm',city:'Farmington',state:'NM',lat:36.7281,lon:-108.2187},
    'durango herald':{id:'durango-co',city:'Durango',state:'CO',lat:37.2753,lon:-107.8801},
    'front - the journal':{id:'cortez-co',city:'Cortez',state:'CO',lat:37.3489,lon:-108.5859},
    'the journal':{id:'cortez-co',city:'Cortez',state:'CO',lat:37.3489,lon:-108.5859},
    'navajo times':{id:'window-rock-az',city:'Window Rock',state:'AZ',lat:35.6806,lon:-109.0526},
    'kob 4':{id:'albuquerque-nm',city:'Albuquerque',state:'NM',lat:35.0844,lon:-106.6504},
    'krqe':{id:'albuquerque-nm',city:'Albuquerque',state:'NM',lat:35.0844,lon:-106.6504},
    'koat':{id:'albuquerque-nm',city:'Albuquerque',state:'NM',lat:35.0844,lon:-106.6504},
    'denver7':{id:'denver-co',city:'Denver',state:'CO',lat:39.7392,lon:-104.9903},
    'the denver post':{id:'denver-co',city:'Denver',state:'CO',lat:39.7392,lon:-104.9903},
    'krdo':{id:'colorado-springs-co',city:'Colorado Springs',state:'CO',lat:38.8339,lon:-104.8214}
  };
  const LOCAL_MIN_STORIES=8;
  const LOCAL_MAX_MARKETS=3;
  const REGION_MAX_MARKETS=6;
"""
s=s.replace("  const LOCAL_RADIUS_MILES=150;", "  const LOCAL_RADIUS_MILES=150;\n"+market_js)

s=s.replace("  function itemRegion(item){\n    const tagged=field(item,['region']).toLowerCase();if(tagged)return tagged;\n    const code=inferredStateCode(item);return STATE_REGION[code]||'';\n  }", "  function itemRegion(item){\n    const code=inferredStateCode(item);if(code)return STATE_REGION[code]||'';\n    return field(item,['region']).toLowerCase();\n  }")

anchor="  function distanceToUser(item,loc){return distanceMiles(loc,itemCoords(item))}\n"
helpers="""  function sourceName(item){return (item.querySelector('source')?.textContent||'').trim().toLowerCase()}
  function sourceMarket(item){
    const src=sourceName(item);
    for(const [key,market] of Object.entries(NEWS_MARKETS)){if(src===key||src.includes(key))return market}
    return null;
  }
  function marketDistance(market,loc){return distanceMiles(loc,market)}
  function marketGroups(items,loc){
    const groups=new Map();
    items.forEach(item=>{
      const market=sourceMarket(item);if(!market)return;
      if(!groups.has(market.id))groups.set(market.id,{market,items:[]});
      groups.get(market.id).items.push(item);
    });
    return [...groups.values()].map(g=>({...g,d:marketDistance(g.market,loc)})).filter(g=>g.d!=null).sort((a,b)=>a.d-b.d);
  }
"""
if helpers.strip() not in s:
    s=s.replace(anchor,anchor+helpers)

old=re.search(r"  function localPool\(items\)\{.*?\n  \}\n\n  function regionPool\(items\)\{.*?\n  \}\n", s, flags=re.S)
if not old:
    raise SystemExit('local/region pool block not found')
new="""  function nearestLocalSelection(items,loc){
    const candidates=items.filter(i=>['local','region','nm'].includes(category(i)));
    const selected=[];const seen=new Set();const usedMarkets=[];
    const add=arr=>rank(arr,loc).forEach(item=>{const k=itemKey(item);if(k&&!seen.has(k)){seen.add(k);selected.push(item)}});

    add(items.filter(i=>['local','region','nm','us','top'].includes(category(i))&&matchesCity(i,loc)&&matchesState(i,loc)));

    for(const group of marketGroups(candidates,loc)){
      if(selected.length>=LOCAL_MIN_STORIES||usedMarkets.length>=LOCAL_MAX_MARKETS)break;
      add(group.items);usedMarkets.push(group.market.id);
    }
    return {selected,usedMarkets};
  }

  function localPool(items){
    const loc=location();if(!loc.city&&!loc.code&&loc.lat==null)return [];
    const result=nearestLocalSelection(items,loc);
    return result.selected.map(i=>cloneAs(i,'local','Nearest active news market')).slice(0,90);
  }

  function regionPool(items){
    const loc=location();if(!loc.city&&!loc.code&&loc.lat==null)return [];
    const local=nearestLocalSelection(items,loc);
    const used=new Set(local.usedMarkets);
    const localKeys=new Set(local.selected.map(itemKey));
    const regional=[];const seen=new Set();let marketCount=0;
    const add=arr=>rank(arr,loc).forEach(item=>{const k=itemKey(item);if(k&&!localKeys.has(k)&&!seen.has(k)){seen.add(k);regional.push(item)}});

    const candidates=items.filter(i=>['local','region','nm'].includes(category(i)));
    for(const group of marketGroups(candidates,loc)){
      if(used.has(group.market.id))continue;
      add(group.items);marketCount++;
      if(marketCount>=REGION_MAX_MARKETS||regional.length>=12)break;
    }

    // Collector-confirmed regional stories are the safe fallback when publisher-market
    // metadata is incomplete. Exclude anything already displayed in Local.
    if(regional.length<5)add(items.filter(i=>category(i)==='region'));
    return regional.map(i=>cloneAs(i,'region','Next closest news markets')).slice(0,90);
  }
"""
s=s[:old.start()]+new+s[old.end():]

s=s.replace("  window.__locationContentV28=true;", "  window.__locationMarketPolicyV32={minLocalStories:8,maxLocalMarkets:3,maxRegionMarkets:6};\n  window.__locationContentV28=true;\n  window.__locationContentV29=true;\n  window.__locationContentV30=true;\n  window.__locationContentV31=true;\n  window.__locationContentV32=true;")

p.write_text(s,encoding='utf-8')
print('Applied V32 nearest-active-market test with collector-confirmed regional fallback and Local/Region overlap protection.')
