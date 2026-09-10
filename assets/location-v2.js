(function(){
  'use strict';
  const CACHE_KEY='underreported-location-v2';
  const MAX_AGE=6*60*60*1000;
  let pending=null;

  function readCache(){
    try{
      const v=JSON.parse(localStorage.getItem(CACHE_KEY)||'null');
      if(v&&v.lat!=null&&v.lon!=null&&Date.now()-Number(v.savedAt||0)<MAX_AGE)return v;
    }catch(e){}
    return null;
  }
  function legacy(){
    const label=localStorage.getItem('underreported-location')||'';
    const state=localStorage.getItem('underreported-state')||((label.match(/,\s*([A-Z]{2})$/)||[])[1]||'');
    return {label,state};
  }
  function persist(v){
    const out={...v,savedAt:Date.now()};
    try{
      localStorage.setItem(CACHE_KEY,JSON.stringify(out));
      if(out.state)localStorage.setItem('underreported-state',String(out.state).toUpperCase());
      if(out.label)localStorage.setItem('underreported-location',out.label);
    }catch(e){}
    window.dispatchEvent(new CustomEvent('underreported:location',{detail:out}));
    return out;
  }
  function browserCoords(){
    return new Promise((resolve,reject)=>{
      if(!navigator.geolocation)return reject(new Error('Geolocation unavailable'));
      navigator.geolocation.getCurrentPosition(
        p=>resolve({lat:p.coords.latitude,lon:p.coords.longitude,accuracy:p.coords.accuracy,source:'device'}),
        reject,
        {enableHighAccuracy:false,maximumAge:15*60*1000,timeout:6000}
      );
    });
  }
  async function ipCoords(){
    const r=await fetch('https://ipapi.co/json/',{cache:'no-store'});
    if(!r.ok)throw new Error('IP location unavailable');
    const d=await r.json();
    if(d.latitude==null||d.longitude==null)throw new Error('IP location incomplete');
    const state=(d.region_code||'').toUpperCase();
    const city=d.city||'';
    return {lat:Number(d.latitude),lon:Number(d.longitude),city,state,label:[city,state].filter(Boolean).join(', '),source:'ip'};
  }
  async function resolve(force){
    if(!force){const cached=readCache();if(cached)return cached;}
    const old=legacy();
    try{
      const coords=await browserCoords();
      return persist({...coords,state:old.state||'',label:old.label||''});
    }catch(e){
      try{return persist(await ipCoords());}
      catch(ipError){
        const cached=readCache();
        if(cached)return cached;
        throw ipError;
      }
    }
  }

  window.UnderreportedLocation={
    get(options={}){
      const force=Boolean(options.force);
      if(!force&&pending)return pending;
      pending=resolve(force).finally(()=>{pending=null;});
      return pending;
    },
    cached:readCache,
    clear(){try{localStorage.removeItem(CACHE_KEY);}catch(e){}},
  };
})();
