import worker,{FeedState as ExistingFeedState} from "./cloudflare-entry.js";
import {compactElasticPool,recalcStatus} from "./pool-maintenance.js";

const DAILY_REBUILD_CRON="13 10 * * *";
const FEEDBACK_REASONS=["D","NR","NW"];

function decodeEntities(value=""){
  return String(value)
    .replace(/&amp;/gi,"&")
    .replace(/&quot;/gi,'"')
    .replace(/&#39;|&apos;/gi,"'")
    .replace(/&lt;/gi,"<")
    .replace(/&gt;/gi,">")
    .replace(/&#(\d+);/g,(_,n)=>{const code=Number(n);return Number.isFinite(code)?String.fromCodePoint(code):_})
    .replace(/&#x([0-9a-f]+);/gi,(_,n)=>{const code=parseInt(n,16);return Number.isFinite(code)?String.fromCodePoint(code):_});
}
function plainText(value=""){
  let text=String(value??"").replace(/<!\[CDATA\[([\s\S]*?)\]\]>/gi,"$1");
  for(let i=0;i<3;i++){
    const before=text;
    text=decodeEntities(text).replace(/<\/?[a-z][^>]*>/gi," ");
    if(text===before)break;
  }
  return text.replace(/\s+/g," ").trim();
}
function normalize(value=""){return plainText(value).toLowerCase().replace(/\s+/g," ").trim()}
function sanitizeStory(row){
  if(!row||typeof row!=="object")return row;
  const story={...row};
  const fields=["title","summary","why_matters","what_happened","what_is_missing","background","what_next","source"];
  for(const field of fields)if(story[field]!=null)story[field]=plainText(story[field]);
  if(story.summary&&normalize(story.summary)===normalize(story.title))story.summary="";
  if(story.summary&&normalize(story.summary).startsWith(normalize(story.title))&&story.summary.length<=story.title.length+80)story.summary="";
  return story;
}
function sanitizeFeed(feed){
  const next={...feed,stories:{...(feed.stories||{})},reserves:{...(feed.reserves||{})}};
  for(const [key,rows] of Object.entries(next.stories))next.stories[key]=(rows||[]).map(sanitizeStory);
  for(const [key,rows] of Object.entries(next.reserves))next.reserves[key]=(rows||[]).map(sanitizeStory);
  return next;
}
function feedbackKey(reason){return `feedback:${reason}`}
function recordMatchesStory(record,story,category,reason){
  if(reason!=="D"&&normalize(record.category)!==normalize(category))return false;
  const ru=normalize(record.url_key||record.url),su=normalize(story.url);
  if(ru&&su&&ru===su)return true;
  return normalize(record.title_key||record.title)===normalize(story.title)&&normalize(record.source_key||record.source)===normalize(story.source);
}
function applyFeedbackSuppression(feed,pools){
  const next={...feed,stories:{...(feed.stories||{})},reserves:{...(feed.reserves||{})}};
  let removed=0;
  for(const bucket of ["stories","reserves"]){
    for(const [category,rows] of Object.entries(next[bucket])){
      const before=(rows||[]).length;
      next[bucket][category]=(rows||[]).filter(story=>!FEEDBACK_REASONS.some(reason=>(pools[reason]||[]).some(record=>recordMatchesStory(record,story,category,reason))));
      removed+=before-next[bucket][category].length;
    }
  }
  return{feed:next,removed};
}
function feedbackCounts(pools){return Object.fromEntries(FEEDBACK_REASONS.map(reason=>[reason,(pools[reason]||[]).length]))}

const NW_STOP=new Set(["the","and","for","with","from","this","that","news","latest","update","updates","report","reports","page","new"]);
const NW_PATTERNS=[
  {name:"generic-news",re:/^(?:nfl )?news(?:\s*&\s*analysis)?$/i},
  {name:"profile-updates",re:/^.+? news,? rumors,? (?:&|and) updates$/i},
  {name:"paginated-index",re:/^.+?\s*\|\s*page\s+\d+/i},
  {name:"breaking-news",re:/^breaking news$/i}
];
function nwTokens(value=""){return new Set((normalize(value).match(/[a-z0-9]+/g)||[]).filter(x=>x.length>=4&&!NW_STOP.has(x)))}
function feedbackTokens(value=""){return [...nwTokens(value)]}
function learnRoutes(pools){
  const groups=new Map();
  for(const row of (pools.NR||[])){
    const origin=normalize(row.original_category||row.category),target=normalize(row.target_category||row.targetCategory);
    if(!origin||!target||origin===target)continue;
    const key=origin+"=>"+target;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);
  }
  const routes=[];
  for(const [key,rows] of groups){if(rows.length<2)continue;const [origin,target]=key.split("=>"),counts=new Map();for(const row of rows)for(const token of feedbackTokens(row.title))counts.set(token,(counts.get(token)||0)+1);const tokens=[...counts].filter(([,n])=>n>=2).map(([t])=>t);if(tokens.length)routes.push({origin,target,tokens,examples:rows.length})}
  return routes;
}
function learnFeedback(pools){
  const rows=pools.NW||[],structural=[];
  for(const rule of NW_PATTERNS){const examples=rows.filter(r=>rule.re.test(normalize(r.title))).length;if(examples>=2)structural.push({name:rule.name,examples})}
  const vagueSignals=new Map();
  for(const row of rows){
    const title=normalize(row.title),tokens=[...nwTokens(title)];
    const signals=[];
    if(tokens.length<=3)signals.push("very-short");
    if(!/\b(?:who|what|when|where|why|how)\b/.test(title)&&tokens.length<=5)signals.push("low-context");
    if(/^(?:watch|live|here(?:'s| is)|more|details|what we know|developing|just in)\b/i.test(title))signals.push("generic-lead");
    if(!/[a-z0-9].*\s.*[a-z0-9]/i.test(title))signals.push("fragment");
    for(const s of signals)vagueSignals.set(s,(vagueSignals.get(s)||0)+1);
  }
  const vague=[...vagueSignals].filter(([,examples])=>examples>=2).map(([name,examples])=>({name,examples}));
  return{version:3,nwStructural:structural,nwVague:vague,nwExamples:rows.length,nrRoutes:learnRoutes(pools),nrExamples:(pools.NR||[]).length,dExamples:(pools.D||[]).length,updatedAt:new Date().toISOString()};
}
function nwLearnedReject(story,learning){
  const title=normalize(story?.title||"");
  if((learning?.nwStructural||[]).some(x=>NW_PATTERNS.find(p=>p.name===x.name)?.re.test(title)))return true;
  const enabled=new Set((learning?.nwVague||[]).map(x=>x.name)),tokens=[...nwTokens(title)];
  if(enabled.has("very-short")&&tokens.length<=3)return true;
  if(enabled.has("low-context")&&!/\b(?:who|what|when|where|why|how)\b/.test(title)&&tokens.length<=5)return true;
  if(enabled.has("generic-lead")&&/^(?:watch|live|here(?:'s| is)|more|details|what we know|developing|just in)\b/i.test(title))return true;
  if(enabled.has("fragment")&&!/[a-z0-9].*\s.*[a-z0-9]/i.test(title))return true;
  return false;
}
function learnedRoute(story,category,learning){
  const tokens=nwTokens(story?.title||"");
  for(const rule of (learning?.nrRoutes||[]))if(normalize(category)===rule.origin&&rule.tokens.some(t=>tokens.has(t)))return rule.target;
  return "";
}
function applyLearnedFeedback(feed,learning){
  const next={...feed,stories:{...(feed.stories||{})},reserves:{...(feed.reserves||{})}};let removed=0;
  const routed=[];for(const bucket of ["stories","reserves"])for(const [category,rows] of Object.entries(next[bucket])){const before=(rows||[]).length;const kept=[];for(const story of (rows||[])){if(nwLearnedReject(story,learning)){removed++;continue}const target=learnedRoute(story,category,learning);if(target&&target!==category){next[bucket][target]=next[bucket][target]||[];next[bucket][target].push({...story,category:target});routed.push({from:category,to:target,title:story.title});continue}kept.push(story)}next[bucket][category]=kept}
  return{feed:next,removed,routed};
}

async function saveMaintenance(state,status,{daily=false}={}){
  const seeded=await state.seed();
  const pools=await state.feedbackPools();
  const sanitized=sanitizeFeed(structuredClone(seeded.feed));
  const suppressed=applyFeedbackSuppression(sanitized,pools);\n  const learning=learnFeedback(pools);\n  const learned=applyLearnedFeedback(suppressed.feed,learning);\n  const maintained=compactElasticPool(learned.feed,status,{daily});
  const generatedAt=status.generatedAt||new Date().toISOString();
  maintained.feed.generatedAt=generatedAt;
  maintained.feed.cloudflareRuntime=true;
  maintained.status={...recalcStatus(maintained.feed,maintained.status),generatedAt,cloudflareRuntime:true,feedbackPoolCounts:feedbackCounts(pools),feedbackPoolTotal:FEEDBACK_REASONS.reduce((n,r)=>n+(pools[r]||[]).length,0),feedbackSuppressedLastPass:suppressed.removed,feedbackLearnedSuppressedLastPass:learned.removed,feedbackLearnedRoutedLastPass:learned.routed.length,feedbackLearning:learning};
  if(daily){
    maintained.status.dailyRebuild={
      at:new Date().toISOString(),
      removed:maintained.removed,
      poolStoryCount:maintained.status.poolStoryCount,
      reserveStoryCount:maintained.status.reserveStoryCount
    };
  }
  await state.ctx.storage.put({feed:maintained.feed,status:maintained.status});
  return maintained.status;
}

export class FeedState extends ExistingFeedState{
  async feedbackPools(){
    const values=await Promise.all(FEEDBACK_REASONS.map(reason=>this.ctx.storage.get(feedbackKey(reason))));
    return Object.fromEntries(FEEDBACK_REASONS.map((reason,i)=>[reason,Array.isArray(values[i])?values[i]:[]]));
  }

  async submitFeedback(payload){
    const reason=String(payload?.reason||"").toUpperCase();
    if(!FEEDBACK_REASONS.includes(reason))throw new Error("invalid feedback reason");
    const record={
      reason,
      category:plainText(payload?.category||""),
      title:plainText(payload?.title||""),
      url:String(payload?.url||"").trim(),
      source:plainText(payload?.source||""),
      description:plainText(payload?.description||""),
      why:plainText(payload?.why||""),
      published_at:plainText(payload?.publishedAt||payload?.published_at||""),
      image_url:String(payload?.imageUrl||payload?.image_url||"").trim(),
      story_id:String(payload?.storyId||payload?.story_id||"").trim(),
      original_category:plainText(payload?.originalCategory||payload?.category||""),
      target_category:plainText(payload?.targetCategory||payload?.target_category||""),
      schema_version:Number(payload?.schemaVersion||2),
      captured_at:payload?.capturedAt||new Date().toISOString(),
      title_key:normalize(payload?.title||""),
      url_key:normalize(payload?.url||""),
      source_key:normalize(payload?.source||"")
    };
    if(!record.title&&!record.url)throw new Error("feedback requires a story");
    const pools=await this.feedbackPools();
    const rows=pools[reason];
    const duplicate=rows.some(r=>recordMatchesStory(r,record,record.category,reason));
    if(!duplicate)rows.unshift(record);
    if(rows.length>5000)rows.length=5000;
    pools[reason]=rows;
    await this.ctx.storage.put(feedbackKey(reason),rows);

    const seeded=await this.seed();
    const suppressed=applyFeedbackSuppression(sanitizeFeed(structuredClone(seeded.feed)),pools);\n    const learning=learnFeedback(pools);\n    const learned=applyLearnedFeedback(suppressed.feed,learning);\n    const status={...recalcStatus(learned.feed,seeded.status||{}),feedbackPoolCounts:feedbackCounts(pools),feedbackPoolTotal:FEEDBACK_REASONS.reduce((n,r)=>n+(pools[r]||[]).length,0),feedbackLastWriteAt:new Date().toISOString(),feedbackLearning:learning,feedbackLearnedSuppressedLastPass:learned.removed,feedbackLearnedRoutedLastPass:learned.routed.length,cloudflareRuntime:true};\n    await this.ctx.storage.put({feed:learned.feed,status,feedbackLearning:learning});\n    return{ok:true,record,counts:feedbackCounts(pools),removedFromFeed:suppressed.removed,removedByLearning:learned.removed,routedByLearning:learned.routed.length,learning};
  }

  async refresh(){
    const status=await super.refresh();
    return saveMaintenance(this,status,{daily:false});
  }

  async rebuild(){
    await this.ctx.storage.put("cursor",0);
    const before=(await this.seed()).status||{};
    const status=await super.refresh();
    const rebuilt=await saveMaintenance(this,status,{daily:true});
    rebuilt.dailyRebuild={
      ...(rebuilt.dailyRebuild||{}),
      beforePoolStoryCount:Number(before.poolStoryCount||0),
      beforeReserveStoryCount:Number(before.reserveStoryCount||0),
      sourceSweepReset:true
    };
    await this.ctx.storage.put({status:rebuilt,lastDailyRebuild:rebuilt.dailyRebuild});
    return rebuilt;
  }

  async fetch(request){
    const url=new URL(request.url),path=url.pathname;
    if(path==="/rebuild"&&request.method==="POST"){
      try{return Response.json(await this.rebuild())}
      catch(error){return Response.json({ok:false,error:String(error?.message||error)},{status:503})}
    }
    if(path==="/feedback"){
      try{
        if(request.method==="GET"){
          const pools=await this.feedbackPools();
          return Response.json({ok:true,pools,counts:feedbackCounts(pools)});
        }
        if(request.method==="POST")return Response.json(await this.submitFeedback(await request.json()));
        return new Response("Method not allowed",{status:405});
      }catch(error){return Response.json({ok:false,error:String(error?.message||error)},{status:400})}
    }
    return super.fetch(request);
  }
}

export default{
  ...worker,
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(url.pathname==="/api/feedback"){
      const target=new Request(`https://state/feedback${url.search}`,request);
      const response=await env.FEED_STATE.getByName("production").fetch(target);
      const headers=new Headers(response.headers);headers.set("Cache-Control","no-store");
      return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
    }
    return worker.fetch(request,env,ctx);
  },
  async scheduled(controller,env,ctx){
    const path=controller.cron===DAILY_REBUILD_CRON?"/rebuild":"/refresh";
    ctx.waitUntil((async()=>{
      const response=await env.FEED_STATE.getByName("production").fetch(`https://state${path}`,{method:"POST"});
      if(!response.ok)console.error(`Cloudflare collector ${path} failed`,await response.text());
    })());
  }
};
