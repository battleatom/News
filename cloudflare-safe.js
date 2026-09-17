import worker,{FeedState} from "./cloudflare-services.js";

export {FeedState};

const SAFE_JSON=new Set(["/feed.json","/status.json","/nfl.json","/boxoffice.json","/markets.json"]);

function noStore(response){
  const headers=new Headers(response.headers);
  headers.set("Cache-Control","no-store, no-cache, max-age=0, must-revalidate");
  headers.set("Pragma","no-cache");
  headers.set("Expires","0");
  return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}

async function assetFallback(path,env){
  try{
    const fallback=await env.ASSETS.fetch(`https://asset${path}`);
    if(fallback.ok)return noStore(fallback);
    return fallback;
  }catch(error){
    return Response.json({ok:false,error:`Cloudflare fallback failed: ${String(error?.message||error)}`},{status:503,headers:{"Cache-Control":"no-store"}});
  }
}

export default{
  ...worker,
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(!SAFE_JSON.has(url.pathname))return worker.fetch(request,env,ctx);
    try{
      const response=await worker.fetch(request,env,ctx);
      if(response.ok)return response;
      console.warn(`Live ${url.pathname} returned ${response.status}; serving bundled fallback`);
      return assetFallback(url.pathname,env);
    }catch(error){
      console.warn(`Live ${url.pathname} threw; serving bundled fallback`,error);
      return assetFallback(url.pathname,env);
    }
  },
  async scheduled(controller,env,ctx){return worker.scheduled(controller,env,ctx)}
};
