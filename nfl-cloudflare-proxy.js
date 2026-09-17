(()=>{
  const original=window.fetch.bind(window);
  window.fetch=(input,init)=>{
    try{
      const raw=typeof input==='string'?input:input?.url||'';
      const parsed=new URL(raw,location.href);
      let next=null;
      if(parsed.pathname.endsWith('/functions/v1/nfl-live')){
        next=new URL('/api/nfl-live',location.origin);
      }else if(parsed.pathname==='/apis/site/v2/sports/football/nfl/scoreboard'){
        next=new URL('/api/nfl-scoreboard',location.origin);
      }else if(parsed.pathname==='/apis/site/v2/sports/football/nfl/summary'){
        next=new URL('/api/nfl-summary',location.origin);
      }
      if(next){
        for(const [k,v] of parsed.searchParams)next.searchParams.set(k,v);
        if(typeof input==='string')return original(next.toString(),init);
        return original(new Request(next.toString(),input),init);
      }
    }catch{}
    return original(input,init);
  };
})();
