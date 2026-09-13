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
    const state=(localStorage.getItem('underreported-state')||((label.match(/,\s*([A-Z]{2})$/)||[])[1]||'')).toUpperCase();
    const county=localStorage.getItem('underreported-county')||'';
    return {label,state,county};
  }
  function persist(v){
    const state=String(v.state||'').replace(/^US-/,'').toUpperCase();
    const county=String(v.county||'').trim();
    const label=v.label||[v.city,state].filter(Boolean).join(', ');
    const out={...v,state,county,label,savedAt:Date.now()};
    try{
      localStorage.setItem(CACHE_KEY,JSON.stringify(out));
      if(state)localStorage.setItem('underreported-state',state);
      if(county)localStorage.setItem('underreported-county',county);
      if(label)localStorage.setItem('underreported-location',label);
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
  function countyFromReverse(d){
    const direct=String(d.county||d.countyName||'').trim();
    if(direct)return direct;
    const admin=Array.isArray(d.localityInfo?.administrative)?d.localityInfo.administrative:[];
    const named=admin.map(x=>String(x?.name||'').trim()).filter(Boolean);
    return named.find(n=>/(county|parish|borough|census area|municipality)$/i.test(n))||'';
  }
  async function reverseGeocode(coords){
    try{
      const q=new URLSearchParams({latitude:String(coords.lat),longitude:String(coords.lon),localityLanguage:'en'});
      const r=await fetch('https://api.bigdatacloud.net/data/reverse-geocode-client?'+q,{cache:'no-store'});
      if(!r.ok)throw new Error('reverse geocode unavailable');
      const d=await r.json();
      const state=String(d.principalSubdivisionCode||'').replace(/^US-/,'').toUpperCase();
      const city=d.city||d.locality||'';
      const county=countyFromReverse(d);
      return {...coords,city,state,county,label:[city,state].filter(Boolean).join(', ')};
    }catch(e){return coords;}
  }
  async function ipCoords(){
    const r=await fetch('https://ipapi.co/json/',{cache:'no-store'});
    if(!r.ok)throw new Error('IP location unavailable');
    const d=await r.json();
    if(d.latitude==null||d.longitude==null)throw new Error('IP location incomplete');
    const state=(d.region_code||'').toUpperCase(),city=d.city||'';
    return {lat:Number(d.latitude),lon:Number(d.longitude),city,state,county:'',label:[city,state].filter(Boolean).join(', '),source:'ip'};
  }
  async function resolve(force){
    if(!force){const cached=readCache();if(cached)return cached;}
    const old=legacy();
    try{
      let coords=await browserCoords();
      coords=await reverseGeocode(coords);
      if(coords.state)return persist(coords);
      try{return persist(await ipCoords());}
      catch(ipError){
        if(old.state||old.label)return persist({...coords,state:old.state,county:old.county,label:old.label,source:'device-unresolved'});
        return persist(coords);
      }
    }catch(e){
      try{return persist(await ipCoords());}
      catch(ipError){const cached=readCache();if(cached)return cached;throw ipError;}
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
    clear(){
      try{
        localStorage.removeItem(CACHE_KEY);
        localStorage.removeItem('underreported-location');
        localStorage.removeItem('underreported-state');
        localStorage.removeItem('underreported-county');
      }catch(e){}
    },
  };
})();

/* Version 3 presentation layer loader. Kept separate from feed/update logic. */
(function(){
  if(document.querySelector('script[data-underreported-v3-ui]'))return;
  const s=document.createElement('script');
  s.src='assets/v3-ui.js?v=3';
  s.defer=true;
  s.dataset.underreportedV3Ui='true';
  document.head.appendChild(s);
})();