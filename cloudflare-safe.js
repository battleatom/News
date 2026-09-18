import worker,{FeedState} from "./cloudflare-services.js";

export {FeedState};

const SAFE_JSON=new Set(["/feed.json","/status.json","/nfl.json","/boxoffice.json","/markets.json"]);
const VALIDATED_ASSET_JSON=new Set(["/feed.json","/status.json","/boxoffice.json"]);

function noStore(response,extraHeaders={}){
  const headers=new Headers(response.headers);
  headers.set("Cache-Control","no-store, no-cache, max-age=0, must-revalidate");
  headers.set("Pragma","no-cache");
  headers.set("Expires","0");
  for(const [key,value] of Object.entries(extraHeaders))headers.set(key,value);
  return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}

async function assetJson(path,env,{fallback=false}={}){
  try{
    const response=await env.ASSETS.fetch(`https://asset${path}`);
    if(!response.ok)return response;
    const value=await response.json();
    value.cloudflareRuntime=true;
    value.runtimeSource="validated-v6-github-build";
    if(path==="/status.json")value.buildMode="validated-v6-github-build";
    return noStore(Response.json(value),{"X-Underreported-Fallback":fallback?"1":"0","X-Underreported-Data-Source":"validated-v6-github-build"});
  }catch(error){
    return Response.json({ok:false,error:`Cloudflare asset read failed: ${String(error?.message||error)}`},{status:503,headers:{"Cache-Control":"no-store","X-Underreported-Fallback":fallback?"1":"0"}});
  }
}
async function assetFallback(path,env){return assetJson(path,env,{fallback:true})}
async function validatedHealth(env){
  const response=await env.ASSETS.fetch("https://asset/status.json");
  if(!response.ok)return Response.json({ok:false,error:`status asset ${response.status}`},{status:503,headers:{"Cache-Control":"no-store"}});
  const status=await response.json(),generated=Date.parse(status.generatedAt||""),ageMinutes=Number.isFinite(generated)?Math.max(0,Math.round((Date.now()-generated)/60000)):null,critical=ageMinutes==null||ageMinutes>90,healthState=critical?"stale":ageMinutes>35?"watch":"healthy";
  return Response.json({ok:!critical,healthState,service:"underreported-news",runtime:"cloudflare",dataSource:"validated-v6-github-build",generatedAt:status.generatedAt||null,ageMinutes,storyCount:status.storyCount??null,poolStoryCount:status.poolStoryCount??null,reserveStoryCount:status.reserveStoryCount??null,collectorErrors:Array.isArray(status.collectorErrors)?status.collectorErrors.length:0},{status:critical?503:200,headers:{"Cache-Control":"no-store"}});
}

export default{
  ...worker,
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(url.pathname==="/healthz")return validatedHealth(env);
    if(VALIDATED_ASSET_JSON.has(url.pathname))return assetJson(url.pathname,env);
    if(!SAFE_JSON.has(url.pathname))return worker.fetch(request,env,ctx);
    try{
      const response=await worker.fetch(request,env,ctx);
      if(response.ok)return noStore(response,{"X-Underreported-Fallback":"0"});
      console.warn(`Live ${url.pathname} returned ${response.status}; serving bundled fallback`);
      return assetFallback(url.pathname,env);
    }catch(error){
      console.warn(`Live ${url.pathname} threw; serving bundled fallback`,error);
      return assetFallback(url.pathname,env);
    }
  },
  async scheduled(){return}
};
