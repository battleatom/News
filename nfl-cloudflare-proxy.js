(()=>{
  const original=window.fetch.bind(window);
  const legacy="https://bkcrgfkhgjypvzwubwrh.supabase.co/functions/v1/nfl-live";
  window.fetch=(input,init)=>{
    try{
      const raw=typeof input==="string"?input:input?.url||"";
      if(raw.startsWith(legacy)){
        const oldUrl=new URL(raw),next=new URL('/api/nfl-live',location.origin);
        for(const [k,v] of oldUrl.searchParams)next.searchParams.set(k,v);
        if(typeof input==="string")return original(next.toString(),init);
        return original(new Request(next.toString(),input),init);
      }
    }catch{}
    return original(input,init);
  };
})();
