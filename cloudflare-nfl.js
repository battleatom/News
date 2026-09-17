import runtime,{FeedState} from "./cloudflare-runtime.js";

export {FeedState};

const TEAM_ALIASES={WSH:"WAS",LAR:"LA"};

function normalizeAbbr(value=""){const v=String(value||"").toUpperCase();return TEAM_ALIASES[v]||v}
function easternDate(value){
  const dt=new Date(value);if(Number.isNaN(dt.getTime()))return"";
  const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(dt);
  const get=t=>parts.find(p=>p.type===t)?.value||"";
  return `${get("year")}${get("month")}${get("day")}`;
}
function parseGameId(value=""){
  const m=String(value).match(/^(\d{8})_([A-Z0-9]+)@([A-Z0-9]+)$/i);
  if(!m)return null;
  return{date:m[1],away:normalizeAbbr(m[2]),home:normalizeAbbr(m[3])};
}
function eventTeams(event){
  const competition=(event.competitions||[{}])[0];
  const comps=competition.competitors||[];
  const away=comps.find(x=>x.homeAway==="away")||{},home=comps.find(x=>x.homeAway==="home")||{};
  return{
    awayAbbr:normalizeAbbr(away.team?.abbreviation||""),
    homeAbbr:normalizeAbbr(home.team?.abbreviation||""),
    awayPts:String(away.score??""),
    homePts:String(home.score??"")
  };
}
function clockValue(v){return typeof v==="object"?(v?.displayValue||""):(v||"")}
function periodValue(v){return typeof v==="object"?(v?.number||""):(v||"")}
function normalizePlays(summary){
  let plays=summary?.plays||[];
  if(!plays.length)plays=summary?.drives?.current?.plays||[];
  if(!plays.length)plays=(summary?.drives?.previous||[]).flatMap(x=>x.plays||[]);
  if(!plays.length)plays=summary?.scoringPlays||[];
  return plays.filter(p=>p&&(p.text||p.shortText)).slice(-20).map(p=>({
    clock:clockValue(p.clock),period:periodValue(p.period),text:p.text||p.shortText||""
  }));
}
async function nflLiveResponse(url){
  const parsed=parseGameId(url.searchParams.get("gameID")||"");
  if(!parsed)return Response.json({ok:false,error:"invalid gameID"},{status:400,headers:{"Cache-Control":"no-store"}});
  try{
    const boardUrl=`https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=${parsed.date}&limit=64`;
    const boardRes=await fetch(boardUrl,{headers:{Accept:"application/json"},cf:{cacheTtl:2,cacheEverything:false}});
    if(!boardRes.ok)throw new Error(`ESPN scoreboard ${boardRes.status}`);
    const board=await boardRes.json();
    const event=(board.events||[]).find(e=>{
      const t=eventTeams(e);return easternDate(e.date)===parsed.date&&t.awayAbbr===parsed.away&&t.homeAbbr===parsed.home;
    });
    if(!event)return Response.json({ok:false,error:"game not found",provider:"ESPN via Cloudflare"},{status:404,headers:{"Cache-Control":"no-store"}});
    const summaryRes=await fetch(`https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=${encodeURIComponent(event.id)}`,{headers:{Accept:"application/json"},cf:{cacheTtl:2,cacheEverything:false}});
    const summary=summaryRes.ok?await summaryRes.json():{};
    const teams=eventTeams(event),statusType=event.status?.type||{},detail=statusType.shortDetail||statusType.detail||statusType.description||"";
    const period=event.status?.period||summary?.header?.competitions?.[0]?.status?.period||"";
    const clock=event.status?.displayClock||summary?.header?.competitions?.[0]?.status?.displayClock||"";
    return Response.json({
      ok:true,
      provider:"ESPN via Cloudflare",
      fetchedAt:new Date().toISOString(),
      eventId:String(event.id||""),
      game:{
        awayPts:teams.awayPts,
        homePts:teams.homePts,
        currentPeriod:period,
        gameClock:clock,
        gameStatus:detail,
        state:statusType.state||"",
        plays:normalizePlays(summary)
      }
    },{headers:{"Cache-Control":"no-store, max-age=0","Access-Control-Allow-Origin":"*"}});
  }catch(error){
    return Response.json({ok:false,error:String(error?.message||error),provider:"ESPN via Cloudflare"},{status:502,headers:{"Cache-Control":"no-store"}});
  }
}

export default{
  ...runtime,
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(url.pathname==="/api/nfl-live")return nflLiveResponse(url);
    return runtime.fetch(request,env,ctx);
  },
  async scheduled(controller,env,ctx){return runtime.scheduled(controller,env,ctx)}
};
