const refreshStatus=document.getElementById("refresh-status"),health=document.getElementById("health");
let wasChecking=false,feedCurrentUntil=0;
function parseStatus(text){const parts=String(text||"").split("·").map(x=>x.trim()).filter(Boolean);return{mode:parts[0]||"",count:parts.find(x=>/stories|Feed ready/i.test(x))||"Feed ready",clock:parts.find(x=>/^\d+:\d{2}$/.test(x))||""}}
function formatStatus(raw){const {mode,count,clock}=parseStatus(raw);if(/^Checking/i.test(mode)){wasChecking=true;return `↻ Checking for updates · ${count}`}
if(/^Auto update/i.test(mode)){if(wasChecking){feedCurrentUntil=Date.now()+7000;wasChecking=false}const label=Date.now()<feedCurrentUntil?"✓ Feed current":"✓ Auto update active";return `${label} · ${count}${clock?` · Next check ${clock}`:""}`}
return raw}
function enhance(){if(!refreshStatus)return;const next=formatStatus(refreshStatus.textContent);if(next&&next!==refreshStatus.textContent)refreshStatus.textContent=next}
if(refreshStatus){new MutationObserver(enhance).observe(refreshStatus,{childList:true,characterData:true,subtree:true});enhance();setInterval(enhance,1000)}
if(health&&refreshStatus){new MutationObserver(()=>{if(/update delayed/i.test(health.textContent||"")){const {count,clock}=parseStatus(refreshStatus.textContent);refreshStatus.textContent=`⚠ Update delayed · ${count}${clock?` · Next check ${clock}`:""}`}}).observe(health,{childList:true,characterData:true,subtree:true})}
