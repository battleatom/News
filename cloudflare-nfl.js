import runtime,{FeedState} from "./cloudflare-runtime.js";

export {FeedState};

const ESPN_HOST="https://site.api.espn.com";
const TEAM_ALIASES={WSH:"WAS",LAR:"LA"};
function normalizeAbbr(value=""){const v=String(value||"").toUpperCase();return TEAM_ALIASES[v]||v}
function easternDate(value){const dt=new Date(value);if(Number.isNaN(dt.getTime()))return"";const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(dt),get=t=>parts.find(p=>p.type===t)?.value||"";return`${get("year")}${get("month")}${get("day")}`}
function parseGameId(value=""){const m=String(value).match(/^(\d{8})_([A-Z0-9]+)@([A-Z0-9]+)$/i);return m?{date:m[1],away:normalizeAbbr(m[2]),home:normalizeAbbr(m[3])}:null}
function eventTeams(event){const competition=(event.competitions||[{}])[0],comps=competition.competitors||[],away=comps.find(x=>x.homeAway==="away")||{},home=comps.find(x=>x.homeAway==="home")||{};return{awayAbbr:normalizeAbbr(away.team?.abbreviation||""),homeAbbr:normalizeAbbr(home.team?.abbreviation||""),awayPts:String(away.score??""),homePts:String(home.score??"")}}
function clockValue(v){return typeof v==="object"?(v?.displayValue||""):(v||"")}
function periodValue(v){return typeof v==="object"?(v?.number||""):(v||"")}
function normalizePlays(summary){let plays=summary?.plays||[];if(!plays.length)plays=summary?.drives?.current?.plays||[];if(!plays.length)plays=(summary?.drives?.previous||[]).flatMap(x=>x.plays||[]);if(!plays.length)plays=summary?.scoringPlays||[];return plays.filter(p=>p&&(p.text||p.shortText)).slice(-20).map(p=>({clock:clockValue(p.clock),period:periodValue(p.period),text:p.text||p.shortText||""}))}
async function espnJson(path,params,{ttl=2}={}){const q=params instanceof URLSearchParams?params:new URLSearchParams(params||{}),response=await fetch(`${ESPN_HOST}${path}?${q}`,{headers:{Accept:"application/json","User-Agent":"Mozilla/5.0 Underreported-V6-Cloudflare/1.0"},cf:{cacheTtl:ttl,cacheEverything:true}});if(!response.ok)throw new Error(`ESPN ${response.status}`);const text=await response.text();try{return JSON.parse(text)}catch{throw new Error(`ESPN returned non-JSON: ${text.slice(0,60)}`)}}
async function nflScoreboardResponse(url){try{const params=new URLSearchParams(url.searchParams);params.delete("ts");if(!params.has("limit"))params.set("limit","64");const data=await espnJson('/apis/site/v2/sports/football/nfl/scoreboard',params,{ttl:5});return Response.json(data,{headers:{"Cache-Control":"no-store, max-age=0","Access-Control-Allow-Origin":"*","X-Underreported-Provider":"ESPN via Cloudflare"}})}catch(error){return Response.json({error:String(error?.message||error),provider:"ESPN via Cloudflare"},{status:502,headers:{"Cache-Control":"no-store"}})}}
async function nflStandingsResponse(url){try{const params=new URLSearchParams(url.searchParams);params.delete("ts");if(!params.has("region"))params.set("region","us");if(!params.has("lang"))params.set("lang","en");if(!params.has("contentorigin"))params.set("contentorigin","espn");if(!params.has("type"))params.set("type","0");if(!params.has("level"))params.set("level","2");const data=await espnJson('/apis/v2/sports/football/nfl/standings',params,{ttl:60});return Response.json(data,{headers:{"Cache-Control":"no-store, max-age=0","Access-Control-Allow-Origin":"*","X-Underreported-Provider":"ESPN standings via Cloudflare"}})}catch(error){return Response.json({error:String(error?.message||error),provider:"ESPN standings via Cloudflare"},{status:502,headers:{"Cache-Control":"no-store"}})}}
async function nflSummaryResponse(url){const event=String(url.searchParams.get('event')||'').trim();if(!event)return Response.json({error:'missing event',provider:'ESPN via Cloudflare'},{status:400,headers:{'Cache-Control':'no-store'}});try{const data=await espnJson('/apis/site/v2/sports/football/nfl/summary',new URLSearchParams({event}),{ttl:2});return Response.json(data,{headers:{"Cache-Control":"no-store, max-age=0","Access-Control-Allow-Origin":"*","X-Underreported-Provider":"ESPN via Cloudflare"}})}catch(error){return Response.json({error:String(error?.message||error),provider:"ESPN via Cloudflare"},{status:502,headers:{"Cache-Control":"no-store"}})}}

function gameCenterPayload(summary,situation={}){
  const headerSituation=summary?.header?.competitions?.[0]?.situation||{};
  const sit=Object.keys(situation||{}).length?situation:headerSituation;
  const possession=sit.possession;
  const drive=summary?.drives?.current||{};
  const teamStats=(summary?.boxscore?.teams||[]).map(row=>({
    abbr:String(row?.team?.abbreviation||""),teamId:String(row?.team?.id||""),
    stats:(row?.statistics||[]).map(s=>({name:String(s.name||""),label:String(s.label||s.displayName||""),value:String(s.displayValue??s.value??"")})).slice(0,55)
  }));
  const playerStats=(summary?.boxscore?.players||[]).flatMap(group=>(group.statistics||[]).filter(section=>/pass|rush|receiv|defens/i.test(String(section.name||section.type||""))).map(section=>({
    team:String(group.team?.abbreviation||""),category:String(section.name||section.type||""),
    labels:(section.labels||[]).slice(0,8).map(String),
    athletes:(section.athletes||[]).slice(0,4).map(row=>({name:String(row.athlete?.displayName||row.athlete?.shortName||""),stats:(row.stats||[]).slice(0,8).map(String)}))
  }))).slice(0,12);
  const result={
    field:{
      down:Number.isFinite(Number(sit.down))&&sit.down!=null?Number(sit.down):null,
      distance:Number.isFinite(Number(sit.distance))&&sit.distance!=null?Number(sit.distance):null,
      possessionTeamId:String(typeof possession==="object"?(possession?.id||""):(possession||"")),
      possessionText:String(sit.possessionText||""),
      downDistanceText:String(sit.downDistanceText||sit.shortDownDistanceText||""),
      yardLine:Number.isFinite(Number(sit.yardLine))&&sit.yardLine!=null?Number(sit.yardLine):null,
      awayTimeouts:Number.isFinite(Number(sit.awayTimeouts))&&sit.awayTimeouts!=null?Number(sit.awayTimeouts):null,
      homeTimeouts:Number.isFinite(Number(sit.homeTimeouts))&&sit.homeTimeouts!=null?Number(sit.homeTimeouts):null,
      lastPlayText:String(sit.lastPlay?.text||sit.lastPlay?.shortText||"")
    },
    drive:{
      description:String(drive.description||drive.displayResult||drive.result||""),
      playCount:Number.isFinite(Number(drive.plays?.length))?drive.plays.length:null,
      yards:Number.isFinite(Number(drive.yards))&&drive.yards!=null?Number(drive.yards):null,
      elapsed:String(typeof drive.timeElapsed==="object"?(drive.timeElapsed?.displayValue||""):(drive.timeElapsed||"")),
      teamId:String(drive.team?.id||"")
    },
    plays:normalizePlays(summary),
    teamStats,
    playerStats
  };
  return result;
}

const TANK01_HOST="tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com";
function tank01Plays(body){
  const candidates=[];let visits=0;
  function scan(node,depth=0){
    if(!node||typeof node!=="object"||depth>6||visits++>1500)return;
    if(Array.isArray(node)){for(const row of node.slice(0,300))scan(row,depth+1);return}
    for(const [key,value] of Object.entries(node)){
      if(/play/i.test(key)&&value&&typeof value==="object"){
        const entries=Array.isArray(value)?value:Object.values(value);
        for(const row of entries.slice(0,300)){
          if(!row||typeof row!=="object")continue;
          const text=row.description||row.text||row.playDescription||row.play||row.shortText||row.desc;
          if(typeof text!=="string"||!text.trim())continue;
          const clock=typeof row.clock==="object"?row.clock?.displayValue:row.clock;
          const period=typeof row.period==="object"?row.period?.number:row.period;
          candidates.push({clock:String(row.time||row.gameClock||clock||row.timeRemaining||""),period:String(row.quarter||period||row.currentPeriod||row.qtr||""),text:text.trim()});
        }
      }
      if(value&&typeof value==="object")scan(value,depth+1);
    }
  }
  scan(body);
  const seen=new Set();
  return candidates.filter(p=>{const k=p.period+"|"+p.clock+"|"+p.text;if(seen.has(k))return false;seen.add(k);return true}).slice(-20);
}
async function nflTank01Response(url,env){
  const gameID=String(url.searchParams.get("gameID")||"").trim().toUpperCase();
  if(!/^\d{8}_[A-Z0-9]{2,4}@[A-Z0-9]{2,4}$/.test(gameID))return Response.json({ok:false,provider:"Tank01",error:"invalid_game_id"},{status:400,headers:{"Cache-Control":"no-store"}});
  const key=String(env.TANK01_API_KEY||"").trim();
  if(!key)return Response.json({ok:false,provider:"Tank01",configured:false,error:"tank01_not_configured"},{status:503,headers:{"Cache-Control":"no-store"}});
  try{
    const upstream=new URL("https://"+TANK01_HOST+"/getNFLBoxScore");
    upstream.searchParams.set("gameID",gameID);upstream.searchParams.set("playByPlay","true");upstream.searchParams.set("fantasyPoints","false");
    const result=await fetch(upstream.toString(),{headers:{"X-RapidAPI-Key":key,"X-RapidAPI-Host":TANK01_HOST,Accept:"application/json"},cf:{cacheEverything:true,cacheTtl:15},signal:AbortSignal.timeout(8000)});
    if(!result.ok)throw new Error("Tank01 HTTP "+result.status);
    const payload=await result.json(),body=payload?.body??payload?.response??payload??{};
    if(payload?.statusCode&&Number(payload.statusCode)>=400)throw new Error("Tank01 upstream "+payload.statusCode);
    return Response.json({ok:true,provider:"Tank01",configured:true,fetchedAt:new Date().toISOString(),gameID,plays:tank01Plays(body)},{headers:{"Cache-Control":"no-store","X-Underreported-Provider":"Tank01 via Cloudflare"}});
  }catch(error){return Response.json({ok:false,provider:"Tank01",configured:true,error:String(error?.message||error)},{status:502,headers:{"Cache-Control":"no-store"}})}
}

async function nflGameCenterResponse(url){
  const event=String(url.searchParams.get("event")||"");
  if(!/^\d{5,15}$/.test(event))return Response.json({ok:false,error:"invalid event"},{status:400,headers:{"Cache-Control":"no-store"}});
  try{
    const summary=await espnJson("/apis/site/v2/sports/football/nfl/summary",new URLSearchParams({event}),{ttl:15});
    return Response.json({ok:true,eventId:event,provider:"ESPN via Cloudflare",fetchedAt:new Date().toISOString(),gameCenter:gameCenterPayload(summary)},{headers:{"Cache-Control":"no-store, max-age=0"}});
  }catch(error){return Response.json({ok:false,error:String(error?.message||error)},{status:502,headers:{"Cache-Control":"no-store"}})}
}

async function nflLiveResponse(url){const parsed=parseGameId(url.searchParams.get("gameID")||"");if(!parsed)return Response.json({ok:false,error:"invalid gameID"},{status:400,headers:{"Cache-Control":"no-store"}});try{const board=await espnJson('/apis/site/v2/sports/football/nfl/scoreboard',new URLSearchParams({dates:parsed.date,limit:'64'}),{ttl:2}),event=(board.events||[]).find(e=>{const t=eventTeams(e);return easternDate(e.date)===parsed.date&&t.awayAbbr===parsed.away&&t.homeAbbr===parsed.home});if(!event)return Response.json({ok:false,error:"game not found",provider:"ESPN via Cloudflare"},{status:404,headers:{"Cache-Control":"no-store"}});let summary={};try{summary=await espnJson('/apis/site/v2/sports/football/nfl/summary',new URLSearchParams({event:String(event.id||'')}),{ttl:2})}catch{}const teams=eventTeams(event),statusType=event.status?.type||{},detail=statusType.shortDetail||statusType.detail||statusType.description||"",period=event.status?.period||summary?.header?.competitions?.[0]?.status?.period||"",clock=event.status?.displayClock||summary?.header?.competitions?.[0]?.status?.displayClock||"";return Response.json({ok:true,provider:"ESPN via Cloudflare",fetchedAt:new Date().toISOString(),eventId:String(event.id||""),game:{awayPts:teams.awayPts,homePts:teams.homePts,currentPeriod:period,gameClock:clock,gameStatus:detail,state:statusType.state||"",plays:normalizePlays(summary),gameCenter:gameCenterPayload(summary,event.competitions?.[0]?.situation||{})}},{headers:{"Cache-Control":"no-store, max-age=0","Access-Control-Allow-Origin":"*"}})}catch(error){return Response.json({ok:false,error:String(error?.message||error),provider:"ESPN via Cloudflare"},{status:502,headers:{"Cache-Control":"no-store"}})}}
export default{...runtime,async fetch(request,env,ctx){const url=new URL(request.url);if(url.pathname==="/api/nfl-tank01")return nflTank01Response(url,env);if(url.pathname==="/api/nfl-gamecenter")return nflGameCenterResponse(url);if(url.pathname==="/api/nfl-live")return nflLiveResponse(url);if(url.pathname==="/api/nfl-scoreboard")return nflScoreboardResponse(url);if(url.pathname==="/api/nfl-standings")return nflStandingsResponse(url);if(url.pathname==="/api/nfl-summary")return nflSummaryResponse(url);return runtime.fetch(request,env,ctx)},async scheduled(controller,env,ctx){return runtime.scheduled(controller,env,ctx)}};
