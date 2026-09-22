import worker,{FeedState as BaseFeedState} from "./cloudflare-worker.js";

const API_URL="https://api.thenewsapi.com/v1/news/all";
const MAX_CALLS_24H=90;
const CATEGORY_COOLDOWN_MS=60*60*1000;
const PUBLISHED_WINDOW_MS=24*60*60*1000;
const SELF_HEAL_COOLDOWN_MS=5*60*1000;
const SELF_HEAL_STALE_MS=35*60*1000;
const FALLBACK_PRIORITY=["local","nm","federal","presidential","legislation","underreported","region","world","us","technology","gaming","military","entertainment","top"];
const STALE_HOURS={local:8,nm:8,federal:6,presidential:6,legislation:8,underreported:12,region:8,world:6,us:6,technology:6,gaming:8,military:8,entertainment:8,top:4};
const QUERY={
  local:{search:'"Farmington" | "San Juan County" | "Four Corners"',locale:"us"},
  nm:{search:'"New Mexico"',locale:"us"},
  region:{search:'"New Mexico" | Arizona | Colorado | Utah',locale:"us"},
  federal:{search:'Congress | "federal government" | "Supreme Court"',categories:"politics",locale:"us"},
  presidential:{search:'"White House" | President | administration',categories:"politics",locale:"us"},
  legislation:{search:'Congress | bill | legislation | law',categories:"politics",locale:"us"},
  underreported:{search:'investigation | oversight | infrastructure | "public health" | environment',locale:"us"},
  world:{categories:"general"},
  us:{categories:"general",locale:"us"},
  top:{categories:"general"},
  technology:{categories:"tech"},
  gaming:{search:'gaming | "video game" | PlayStation | Xbox | Nintendo',categories:"tech,entertainment"},
  military:{search:'military | Pentagon | defense | NATO | Army | Navy | "Air Force"'},
  entertainment:{categories:"entertainment"}
};

function normalizeTitle(value=""){return String(value).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}
function storyTime(row){const n=Date.parse(row?.published_at||row?.publishedAt||"");return Number.isFinite(n)?n:0}
function newestAgeHours(rows,now=Date.now()){const newest=Math.max(0,...(rows||[]).map(storyTime));return newest?Math.max(0,(now-newest)/3600000):1e9}
function hash(value){let h=2166136261;for(let i=0;i<value.length;i++){h^=value.charCodeAt(i);h=Math.imul(h,16777619)}return(h>>>0).toString(16)}
function whyMatters(category){
  if(["local","nm","region"].includes(category))return"This fills a local or regional coverage gap with a recent report from an additional news index.";
  if(["federal","presidential","legislation"].includes(category))return"This fills a stale government or policy coverage gap with a recent report from an additional news index.";
  if(category==="technology")return"This fills a technology coverage gap with a recent report from an additional news index.";
  if(category==="gaming")return"This fills a gaming coverage gap with a recent report from an additional news index.";
  if(category==="military")return"This fills a defense or security coverage gap with a recent report from an additional news index.";
  return"This fills a stale or underfilled category using a secondary news index when primary collection was insufficient.";
}
function toRows(data,category){return (Array.isArray(data)?data:[]).map(a=>({
  id:`tnapi-${a.uuid||hash(`${a.url||""}|${a.title||""}`)}`,
  category,
  title:String(a.title||"").trim(),
  url:String(a.url||"").trim(),
  source:String(a.source||"TheNewsAPI"),
  published_at:new Date(a.published_at||Date.now()).toISOString(),
  summary:String(a.description||a.snippet||"").trim(),
  why_matters:whyMatters(category),
  source_id:"thenewsapi",
  fallback_source:"thenewsapi",
  cloudflare_collected:true
})).filter(r=>r.title&&r.url&&Number.isFinite(Date.parse(r.published_at)))}
function mergeCategory(feed,status,category,incoming){
  const current=[...(feed.stories?.[category]||[]),...(feed.reserves?.[category]||[])];
  const seenUrl=new Set(),seenTitle=new Set(),rows=[];
  for(const row of [...incoming,...current].sort((a,b)=>storyTime(b)-storyTime(a))){
    const url=String(row.url||"").trim(),title=normalizeTitle(row.title);
    if((url&&seenUrl.has(url))||(title&&seenTitle.has(title)))continue;
    if(url)seenUrl.add(url);if(title)seenTitle.add(title);rows.push(row);
  }
  const cfg=feed.categories?.[category]||{};
  const visibleTarget=Number(cfg.visible_target||cfg.target||feed.stories?.[category]?.length||50);
  const policyCap=Number(status.poolPolicy?.categories?.[category]?.poolCapacity||0);
  const fallbackCap=Math.max(visibleTarget,Math.round(visibleTarget*1.2));
  const capacity=Math.max(visibleTarget,policyCap||fallbackCap);
  const kept=rows.slice(0,capacity);
  feed.stories={...(feed.stories||{}),[category]:kept.slice(0,visibleTarget)};
  feed.reserves={...(feed.reserves||{}),[category]:kept.slice(visibleTarget)};
  return Math.max(0,kept.filter(r=>r.fallback_source==="thenewsapi").length-current.filter(r=>r.fallback_source==="thenewsapi").length);
}
function recalcStatus(feed,status){
  const categoryCounts={},reserveCounts={};
  for(const key of Object.keys(feed.categories||feed.stories||{})){
    categoryCounts[key]=(feed.stories?.[key]||[]).length;
    reserveCounts[key]=(feed.reserves?.[key]||[]).length;
  }
  const storyCount=Object.values(categoryCounts).reduce((a,b)=>a+b,0),reserveStoryCount=Object.values(reserveCounts).reduce((a,b)=>a+b,0);
  return{...status,storyCount,visibleStoryCount:storyCount,reserveStoryCount,poolStoryCount:storyCount+reserveStoryCount,categoryCounts,reserveCounts};
}

export class FeedState extends BaseFeedState{
  async refresh(){
    let status=await super.refresh();
    try{
      if(!this.env.THE_NEWS_API){
        status={...status,theNewsApi:{enabled:false,reason:"THE_NEWS_API secret not configured",freshnessRecoveryAvailable:false}};
        await this.ctx.storage.put("status",status);return status;
      }
      const seeded=await this.seed(),feed=structuredClone(seeded.feed),now=Date.now();
      let usage=await this.ctx.storage.get("theNewsApiUsage")||{calls:[],lastByCategory:{}};
      usage.calls=(usage.calls||[]).map(Number).filter(ts=>Number.isFinite(ts)&&now-ts<PUBLISHED_WINDOW_MS);
      usage.lastByCategory=usage.lastByCategory||{};
      const weak=[];
      for(const category of FALLBACK_PRIORITY){
        const rows=feed.stories?.[category]||[],cfg=feed.categories?.[category]||{},target=Number(cfg.visible_target||cfg.target||rows.length||0),age=newestAgeHours(rows,now),stale=age>(STALE_HOURS[category]??8),underfilled=target>0&&rows.length<target,last=Number(usage.lastByCategory[category]||0),cooled=now-last>=CATEGORY_COOLDOWN_MS;
        if(cooled&&(stale||underfilled)){const threshold=STALE_HOURS[category]??8,urgency=underfilled?1000:age/threshold;weak.push({category,age,underfilled,threshold,urgency})}
      }
      if(usage.calls.length>=MAX_CALLS_24H||!weak.length){
        status={...status,theNewsApi:{enabled:true,requestsLast24h:usage.calls.length,limit:MAX_CALLS_24H,used:false,reason:usage.calls.length>=MAX_CALLS_24H?"budget reserved":"no stale or underfilled category"}};
        await this.ctx.storage.put({status,theNewsApiUsage:usage});return status;
      }
      weak.sort((a,b)=>b.urgency-a.urgency||b.age-a.age);const pick=weak[0],spec=QUERY[pick.category]||{},params=new URLSearchParams({api_token:this.env.THE_NEWS_API,language:"en",published_after:new Date(now-PUBLISHED_WINDOW_MS).toISOString().slice(0,19),sort:"published_at",limit:"10"});
      for(const[k,v]of Object.entries(spec))if(v)params.set(k,v);
      const response=await fetch(`${API_URL}?${params}`,{headers:{Accept:"application/json"}});
      usage.calls.push(now);usage.lastByCategory[pick.category]=now;
      if(!response.ok){
        const text=(await response.text()).slice(0,240);
        status={...status,theNewsApi:{enabled:true,requestsLast24h:usage.calls.length,limit:MAX_CALLS_24H,used:true,category:pick.category,error:`HTTP ${response.status} ${text}`}};
        await this.ctx.storage.put({status,theNewsApiUsage:usage});return status;
      }
      const payload=await response.json(),rows=toRows(payload?.data,pick.category),added=mergeCategory(feed,status,pick.category,rows),generatedAt=new Date().toISOString();
      feed.generatedAt=generatedAt;feed.cloudflareRuntime=true;
      status=recalcStatus(feed,{...status,generatedAt,theNewsApi:{enabled:true,requestsLast24h:usage.calls.length,limit:MAX_CALLS_24H,used:true,category:pick.category,returned:rows.length,added,staleAgeHours:Math.round(pick.age*10)/10,staleThresholdHours:pick.threshold,urgency:Math.round(pick.urgency*100)/100},cloudflareBatch:{...(status.cloudflareBatch||{}),newsApiUsed:true,newsApiCategory:pick.category,newsApiReturned:rows.length,newsApiAdded:added,newsApiRequestsLast24h:usage.calls.length}});
      await this.ctx.storage.put({feed,status,theNewsApiUsage:usage});
      return status;
    }catch(error){
      status={...status,theNewsApi:{enabled:true,used:false,error:String(error?.message||error)}};
      await this.ctx.storage.put("status",status);return status;
    }
  }

  async fetch(request){
    const path=new URL(request.url).pathname;
    if(path==="/healthz"){
      const seeded=await this.seed(),now=Date.now(),generated=Date.parse(seeded.status?.generatedAt||""),stale=!Number.isFinite(generated)||now-generated>SELF_HEAL_STALE_MS||seeded.status?.cloudflareBatch?.failed;
      const lastAttempt=Number(await this.ctx.storage.get("selfHealAttempt")||0);
      if(stale&&now-lastAttempt>=SELF_HEAL_COOLDOWN_MS){
        await this.ctx.storage.put("selfHealAttempt",now);
        await this.refresh();
      }
    }
    return super.fetch(request);
  }
}

export default worker;
