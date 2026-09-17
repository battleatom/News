import worker,{FeedState as ExistingFeedState} from "./cloudflare-entry.js";
import {compactElasticPool,recalcStatus} from "./pool-maintenance.js";

const DAILY_REBUILD_CRON="13 10 * * *";

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
function normalize(value=""){return plainText(value).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}
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

async function saveMaintenance(state,status,{daily=false}={}){
  const seeded=await state.seed();
  const feed=sanitizeFeed(structuredClone(seeded.feed));
  const maintained=compactElasticPool(feed,status,{daily});
  const generatedAt=status.generatedAt||new Date().toISOString();
  maintained.feed.generatedAt=generatedAt;
  maintained.feed.cloudflareRuntime=true;
  maintained.status={...recalcStatus(maintained.feed,maintained.status),generatedAt,cloudflareRuntime:true};
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
    const path=new URL(request.url).pathname;
    if(path==="/rebuild"&&request.method==="POST"){
      try{return Response.json(await this.rebuild())}
      catch(error){return Response.json({ok:false,error:String(error?.message||error)},{status:503})}
    }
    return super.fetch(request);
  }
}

export default{
  ...worker,
  async scheduled(controller,env,ctx){
    const path=controller.cron===DAILY_REBUILD_CRON?"/rebuild":"/refresh";
    ctx.waitUntil((async()=>{
      const response=await env.FEED_STATE.getByName("production").fetch(`https://state${path}`,{method:"POST"});
      if(!response.ok)console.error(`Cloudflare collector ${path} failed`,await response.text());
    })());
  }
};
