const HOUR=60*60*1000;

function storyTime(row){const n=Date.parse(row?.published_at||row?.publishedAt||"");return Number.isFinite(n)?n:0}
function ageHours(row,now=Date.now()){const t=storyTime(row);return t?Math.max(0,(now-t)/HOUR):1e9}
function views(row){return Number(row?.views||row?.view_count||0)||0}
function quality(row,now){const age=ageHours(row,now);return (views(row)>=10?1000:0)+(age<=12?300:age<=24?200:age<=48?100:0)-age}

export function recalcStatus(feed,status){
  const categoryCounts={},reserveCounts={};
  for(const key of Object.keys(feed.categories||feed.stories||{})){
    categoryCounts[key]=(feed.stories?.[key]||[]).length;
    reserveCounts[key]=(feed.reserves?.[key]||[]).length;
  }
  const storyCount=Object.values(categoryCounts).reduce((a,b)=>a+b,0);
  const reserveStoryCount=Object.values(reserveCounts).reduce((a,b)=>a+b,0);
  return{...status,storyCount,visibleStoryCount:storyCount,reserveStoryCount,poolStoryCount:storyCount+reserveStoryCount,categoryCounts,reserveCounts};
}

export function compactElasticPool(feed,status,{daily=false}={}){
  const now=Date.now();
  let removed=0;
  const detail={};
  feed.reserves={...(feed.reserves||{})};
  for(const key of Object.keys(feed.categories||feed.stories||{})){
    const visible=(feed.stories?.[key]||[]);
    const reserve=[...(feed.reserves?.[key]||[])];
    const cfg=feed.categories?.[key]||{};
    const target=Math.max(1,Number(cfg.visible_target||cfg.target||visible.length||1));
    const fresh=reserve.filter(row=>ageHours(row,now)<=24).length;
    const freshRatio=Math.min(1,fresh/Math.max(1,target));
    const minRatio=daily?.05:.08;
    const maxRatio=daily?.30:.40;
    const desiredRatio=minRatio+(maxRatio-minRatio)*freshRatio;
    let desired=Math.round(target*desiredRatio);
    desired=Math.min(reserve.length,Math.max(0,desired));

    if(daily&&reserve.length>desired){
      const lowValue=reserve.filter(row=>views(row)<10&&ageHours(row,now)>24).length;
      const extra=Math.min(Math.ceil(reserve.length*.10),lowValue);
      desired=Math.max(0,desired-extra);
    }

    reserve.sort((a,b)=>quality(b,now)-quality(a,now)||storyTime(b)-storyTime(a));
    const kept=reserve.slice(0,desired);
    const dropped=reserve.length-kept.length;
    removed+=dropped;
    feed.reserves[key]=kept;
    detail[key]={before:reserve.length,after:kept.length,removed:dropped,fresh24h:fresh,target};
  }
  const nextStatus=recalcStatus(feed,{...status,poolMaintenance:{mode:daily?"daily-rebuild":"elastic-refresh",removed,at:new Date(now).toISOString(),categories:detail}});
  return{feed,status:nextStatus,removed,detail};
}
