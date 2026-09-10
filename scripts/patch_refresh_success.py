from pathlib import Path
import re

P = Path('index.html')
MARKER = 'refresh-success-handling-v1'

s = P.read_text(encoding='utf-8')
if MARKER in s:
    print('Refresh success handling already applied.')
    raise SystemExit(0)

pattern = re.compile(r'async function refreshNewsFromPage\(manual=false\)\{.*?\}\nfunction renderStandardCanonical', re.S)

replacement = r'''async function fetchNewsDocument(){
  const urls=[];
  const addUrl=(u)=>{if(u&&!urls.includes(u))urls.push(u)};
  try{addUrl(new URL('News',document.baseURI).href)}catch(e){}
  try{addUrl(new URL('./News',window.location.href).href)}catch(e){}
  // GitHub Pages project-site fallback. This only runs if the normal relative
  // URL failed and prevents a stale/odd browser base URL from breaking Refresh.
  try{addUrl(new URL('/News/News',window.location.origin).href)}catch(e){}
  let lastError=null;
  for(let attempt=0;attempt<3;attempt++){
    for(const base of urls){
      try{
        const sep=base.includes('?')?'&':'?';
        const response=await fetch(base+sep+'ts='+(Date.now()+attempt),{cache:'no-store'});
        if(!response.ok)throw new Error('HTTP '+response.status);
        const text=await response.text();
        const xml=new DOMParser().parseFromString(text,'text/xml');
        if(xml.querySelector('parsererror'))throw new Error('Invalid RSS/XML feed');
        const items=[...xml.querySelectorAll('channel > item')];
        if(!items.length)throw new Error('News feed returned zero items');
        return {response,text,xml,items};
      }catch(e){lastError=e;}
    }
    if(attempt<2)await new Promise(resolve=>setTimeout(resolve,600*(attempt+1)));
  }
  throw lastError||new Error('Unable to fetch News feed');
}

async function refreshNewsFromPage(manual=false){
  ensurePullStatus();
  const btn=document.getElementById('refresh'),status=document.getElementById('status');
  if(pullInProgress)return false;
  pullInProgress=true;
  if(btn)btn.disabled=true;
  if(status)status.textContent=manual?'Fetching…':'Updating…';
  pullStatusHtml(allItems.length,false,'Connecting to news feed');
  try{
    if(manual)unlockPopAudio();
    const loaded=await fetchNewsDocument();
    const xml=loaded.xml;
    const fetched=loaded.items;
    pullStatusHtml(allItems.length,false,'Feed downloaded');

    const beforeLinks=new Set(allItems.map(normalizeDuplicateKey));
    const result=dedupeFetchedItems(fetched);
    const refreshedItems=result.items;
    const newCount=refreshedItems.filter(item=>!beforeLinks.has(normalizeDuplicateKey(item))).length;
    allItems=refreshedItems;
    if(result.removed)console.info('Client refresh removed',result.removed,'exact duplicate article(s).');

    const channel=xml.querySelector('channel');
    const updated=channel?.querySelector('lastBuildDate')?.textContent||new Date().toISOString();
    const phase=newCount===0?'No new stories — feed is current':(result.removed?`Found ${newCount} new · removed ${result.removed} duplicate${result.removed===1?'':'s'}`:`Found ${newCount} new stor${newCount===1?'y':'ies'}`);
    pullStatusHtml(allItems.length,false,'Rendering updated feed');

    try{
      canonicalBuildTabs();
      canonicalRender(allItems);
      decorateNewBadges();
    }catch(renderError){
      console.error('Feed downloaded successfully, but page rendering failed:',renderError);
      nextScheduledPull=Date.now()+60000;
      window.nextScheduledPull=nextScheduledPull;
      if(status)status.textContent='Feed downloaded · display refresh failed';
      pullStatusHtml(allItems.length,false,'Display refresh failed · retry scheduled');
      return false;
    }

    // Only mark the pull successful after both data validation and rendering succeed.
    lastSuccessfulPull=Date.now();
    nextScheduledPull=lastSuccessfulPull+AUTO_PULL_MS;
    window.lastSuccessfulPull=lastSuccessfulPull;
    window.nextScheduledPull=nextScheduledPull;
    const lastUpdateEl=document.getElementById('last-update');
    if(lastUpdateEl)lastUpdateEl.textContent='Last update: '+formatDate(updated);
    if(status)status.textContent=allItems.length+' stories fetched · '+newCount+' new · '+result.removed+' duplicates removed';
    pullStatusHtml(allItems.length,false,phase);
    if(newCount>0)playNewArticlePop();
    return true;
  }catch(e){
    console.error('News feed refresh failed after retries:',e);
    if(allItems.length){
      if(status)status.textContent='Refresh unavailable · showing '+allItems.length+' current stories';
      pullStatusHtml(allItems.length,false,'Refresh unavailable · current feed kept');
    }else{
      if(status)status.textContent='Update failed';
      pullStatusHtml(0,true,'Unable to fetch or parse feed');
    }
    return false;
  }finally{
    pullInProgress=false;
    if(btn)btn.disabled=false;
  }
}
function renderStandardCanonical'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit('Could not locate canonical refreshNewsFromPage function')

s2 = s2.replace('<script id="site-features-v2">', '<script id="site-features-v2">\n/* '+MARKER+' */', 1)

# The legacy main-script loadNews() has its own broad "Update failed" catch and
# can race the hardened site-features loader. Start the page through the same
# resilient refresh function once every script has been parsed.
legacy_start = 'loadNews();loadMarkets();'
modern_start = "window.addEventListener('DOMContentLoaded',()=>{if(typeof window.refreshNewsFromPage==='function'){window.refreshNewsFromPage(false)}else{loadNews(false)}});loadMarkets();"
if legacy_start in s2:
    s2 = s2.replace(legacy_start, modern_start, 1)

P.write_text(s2, encoding='utf-8')
print('Applied retrying refresh handling and require successful rendering before a pull is marked successful.')
