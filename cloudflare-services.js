import runtime,{FeedState} from "./cloudflare-nfl.js";

export {FeedState};

const ESPN_HOST="https://site.web.api.espn.com";
const MARKET_SYMBOLS=[
  ["^GSPC","S&P 500"],["^DJI","DOW"],["^IXIC","NASDAQ"],["^RUT","RUSSELL 2000"],["^VIX","VIX"],
  ["CL=F","WTI OIL"],["BZ=F","BRENT"],["NG=F","NAT GAS"],["GC=F","GOLD"],["SI=F","SILVER"],
  ["HG=F","COPPER"],["DX-Y.NYB","U.S. DOLLAR"],["^TNX","10Y"],["BTC-USD","BITCOIN"],["ETH-USD","ETHEREUM"]
];

function noStoreJson(value,status=200){return Response.json(value,{status,headers:{"Cache-Control":"no-store, no-cache, max-age=0, must-revalidate"}})}
function dateYmd(dt){return `${dt.getFullYear()}${String(dt.getMonth()+1).padStart(2,"0")}${String(dt.getDate()).padStart(2,"0")}`}
function normalizeGame(event){
  const competition=(event.competitions||[{}])[0],type=event.status?.type||{};
  const teams=(competition.competitors||[]).map(comp=>{const team=comp.team||{};return{name:team.displayName||team.shortDisplayName||"",abbr:team.abbreviation||"",score:String(comp.score??""),homeAway:comp.homeAway||"",logo:team.logo||"",color:team.color||"",alternateColor:team.alternateColor||""}});
  const broadcasts=[...new Set((competition.broadcasts||[]).flatMap(x=>x.names||[]).filter(Boolean))];
  const watch=(event.links||[]).find(x=>(x.rel||[]).some(r=>String(r).toLowerCase().includes("watch")));
  return{id:String(event.id||""),name:event.name||"",shortName:event.shortName||"",date:event.date||"",status:type.description||"",detail:type.shortDetail||type.detail||"",state:type.state||"",teams,broadcasts,watchUrl:watch?.href||"",venue:competition.venue?.fullName||"",plays:[]};
}
async function fetchEspnScoreboard(query){
  const url=`${ESPN_HOST}/apis/site/v2/sports/football/nfl/scoreboard${query?`?${query}`:""}`;
  const r=await fetch(url,{headers:{Accept:"application/json","User-Agent":"Mozilla/5.0 Underreported-V6-Cloudflare/1.0"},cf:{cacheTtl:15}});
  if(!r.ok)throw new Error(`ESPN ${r.status}`);
  const text=await r.text();let d;try{d=JSON.parse(text)}catch{throw new Error(`ESPN returned non-JSON: ${text.slice(0,60)}`)}
  if(!Array.isArray(d?.events))throw new Error("ESPN scoreboard missing events");
  return d;
}
async function nflSchedule(){
  const now=new Date(),from=new Date(now),to=new Date(now);from.setDate(from.getDate()-1);to.setDate(to.getDate()+7);
  const attempts=[`limit=64&dates=${dateYmd(from)}-${dateYmd(to)}`,"limit=64"];
  let lastError=null;
  for(const query of attempts){
    try{
      const d=await fetchEspnScoreboard(query);
      return noStoreJson({generatedAt:new Date().toISOString(),games:(d.events||[]).map(normalizeGame),error:"",provider:"ESPN via Cloudflare",cloudflareRuntime:true});
    }catch(error){lastError=error}
  }
  return noStoreJson({generatedAt:new Date().toISOString(),games:[],error:String(lastError?.message||lastError||"ESPN unavailable"),provider:"ESPN via Cloudflare",cloudflareRuntime:true},502);
}
async function marketRow(symbol,label){
  const url=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=5d&interval=1d`;
  try{const r=await fetch(url,{headers:{Accept:"application/json","User-Agent":"Mozilla/5.0 Underreported-V6-Cloudflare/1.0"},cf:{cacheTtl:300}});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json(),result=d?.chart?.result?.[0]||{},meta=result.meta||{};let price=meta.regularMarketPrice,prev=meta.chartPreviousClose||meta.previousClose||meta.regularMarketPreviousClose;const closes=result?.indicators?.quote?.[0]?.close?.filter(x=>Number.isFinite(x))||[];if(!Number.isFinite(price)&&closes.length){price=closes.at(-1);if(!Number.isFinite(prev)&&closes.length>1)prev=closes.at(-2)}if(!Number.isFinite(price))throw new Error("missing price");const pct=Number.isFinite(prev)&&prev?((price-prev)/prev*100):0;return{symbol,label,price:Math.round(price*100)/100,previousClose:Number.isFinite(prev)?Math.round(prev*100)/100:null,changePct:pct,currency:meta.currency||"USD",marketState:meta.marketState||"",source:"Yahoo Finance via Cloudflare"}}catch(error){return{symbol,label,error:String(error?.message||error),source:"Yahoo Finance via Cloudflare"}}
}
async function markets(){
  const rows=await Promise.all(MARKET_SYMBOLS.map(([symbol,label])=>marketRow(symbol,label))),good=rows.filter(x=>!x.error),errors=rows.filter(x=>x.error);
  return noStoreJson({generatedAt:new Date().toISOString(),markets:good,providerStatus:{sources:["Yahoo Finance via Cloudflare"],instrumentCount:good.length,failed:errors.map(x=>x.symbol),cloudflareRuntime:true},cloudflareRuntime:true,error:errors.length?`${errors.length} market instruments unavailable`:""},good.length?200:502);
}
function cleanHtml(value=""){return String(value).replace(/<script[\s\S]*?<\/script>/gi," ").replace(/<style[\s\S]*?<\/style>/gi," ").replace(/<[^>]+>/g," ").replace(/&amp;/gi,"&").replace(/&quot;/gi,'"').replace(/&#39;|&apos;/gi,"'").replace(/&nbsp;/gi," ").replace(/\s+/g," ").trim()}
function parseShowtimes(html){
  const rows=[],re=/<h2[^>]*>([\s\S]*?)<\/h2>([\s\S]*?)(?=<h2[^>]*>|<\/main>|<\/body>)/gi;let current="",m;
  while((m=re.exec(html))){const heading=cleanHtml(m[1]),body=cleanHtml(m[2]);if(/^(Allen Theatres|AMC |Regal |Cinemark |Harkins )/i.test(heading)){current=heading;continue}const times=body.match(/\b(?:[1-9]|1[0-2]):[0-5]\d\s*(?:am|pm)\b/gi)||[];if(!current||!heading||!times.length)continue;rows.push({title:heading.replace(/\s*Watch Trailer\s*/i,"").trim(),theater:current,showtimes:[...new Set(times.map(x=>x.toLowerCase()))]})}return rows;
}
async function boxOffice(env){
  const seedRes=await env.ASSETS.fetch("https://asset/boxoffice.json");let seed={generatedAt:"",localCity:"Farmington, NM",movies:[]};try{if(seedRes.ok)seed=await seedRes.json()}catch{}
  try{
    const r=await fetch("https://www.showtimes.com/movie-times/farmington-nm/",{headers:{"User-Agent":"Mozilla/5.0 Underreported-V6-Cloudflare/1.0","Accept":"text/html"},cf:{cacheTtl:1800}});if(!r.ok)throw new Error(`showtimes ${r.status}`);const local=parseShowtimes(await r.text());if(!local.length)throw new Error("showtimes parser returned no local movies");const byTitle=new Map((seed.movies||[]).map(movie=>[String(movie.title||"").toLowerCase(),structuredClone(movie)]));const fresh=[];for(const row of local){const key=row.title.toLowerCase(),movie=byTitle.get(key)||{id:`local-${key.replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"")}`,title:row.title,releaseDate:"",overview:"",poster:"",status:"playing",voteAverage:0,rating:"",runtime:"",news:[],source:"Showtimes.com",leavingDate:"",leavingSoon:false};let theater=movie.theaters?.find(x=>x.name===row.theater);if(!theater){theater={name:row.theater,showtimes:[]};movie.theaters=[...(movie.theaters||[]),theater]}theater.showtimes=row.showtimes;movie.status="playing";movie.source="Showtimes.com via Cloudflare";fresh.push(movie)}return noStoreJson({generatedAt:new Date().toISOString(),localCity:seed.localCity||"Farmington, NM",movies:fresh,provider:"Showtimes.com via Cloudflare",cloudflareRuntime:true,error:""})
  }catch(error){return noStoreJson({...seed,generatedAt:new Date().toISOString(),provider:"Cloudflare cached seed",cloudflareRuntime:true,error:`Live showtimes unavailable: ${String(error?.message||error)}`})}
}

export default{
  ...runtime,
  async fetch(request,env,ctx){const url=new URL(request.url);if(url.pathname==="/nfl.json")return nflSchedule();if(url.pathname==="/markets.json")return markets();if(url.pathname==="/boxoffice.json")return boxOffice(env);return runtime.fetch(request,env,ctx)},
  async scheduled(controller,env,ctx){return runtime.scheduled(controller,env,ctx)}
};
