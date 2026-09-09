from pathlib import Path
import re

P = Path('index.html')
MARKER = 'refresh-success-handling-v1'

s = P.read_text(encoding='utf-8')
if MARKER in s:
    print('Refresh success handling already applied.')
    raise SystemExit(0)

pattern = re.compile(r'async function refreshNewsFromPage\(manual=false\)\{.*?\}\nfunction renderStandardCanonical', re.S)

replacement = r'''async function refreshNewsFromPage(manual=false){
  ensurePullStatus();
  const btn=document.getElementById('refresh'),status=document.getElementById('status');
  if(pullInProgress)return false;
  pullInProgress=true;
  if(btn)btn.disabled=true;
  if(status)status.textContent=manual?'Fetching…':'Updating…';
  pullStatusHtml(allItems.length,false,'Connecting to news feed');
  try{
    if(manual)unlockPopAudio();
    const response=await fetch('News?ts='+Date.now(),{cache:'no-store'});
    if(!response.ok)throw new Error('HTTP '+response.status);
    pullStatusHtml(allItems.length,false,'Feed downloaded');
    const text=await response.text();
    const xml=new DOMParser().parseFromString(text,'text/xml');
    if(xml.querySelector('parsererror'))throw new Error('Invalid RSS/XML feed');
    pullStatusHtml(allItems.length,false,'Searching for duplicates');
    const fetched=[...xml.querySelectorAll('item')];
    const beforeLinks=new Set(allItems.map(normalizeDuplicateKey));
    const result=dedupeFetchedItems(fetched);
    allItems=result.items;
    const newCount=allItems.filter(item=>!beforeLinks.has(normalizeDuplicateKey(item))).length;
    if(result.removed)console.info('Client refresh removed',result.removed,'duplicate article(s).');

    // A successfully downloaded and parsed feed is a successful refresh even when
    // it contains zero new stories. Record the successful pull before rendering so
    // the countdown cannot remain at zero after a valid refresh.
    const channel=xml.querySelector('channel');
    const updated=channel?.querySelector('lastBuildDate')?.textContent||new Date().toISOString();
    lastSuccessfulPull=Date.now();
    nextScheduledPull=lastSuccessfulPull+AUTO_PULL_MS;
    window.lastSuccessfulPull=lastSuccessfulPull;
    window.nextScheduledPull=nextScheduledPull;
    document.getElementById('last-update').textContent='Last update: '+formatDate(updated);
    if(status)status.textContent=allItems.length+' stories fetched · '+newCount+' new · '+result.removed+' duplicates removed';

    const phase=newCount===0?'No new stories — feed is current':(result.removed?`Found ${newCount} new · removed ${result.removed} duplicate${result.removed===1?'':'s'}`:`Found ${newCount} new stor${newCount===1?'y':'ies'}`);
    pullStatusHtml(allItems.length,false,phase);

    // Rendering is deliberately separated from feed success. A display-side
    // exception must not falsely report a successful network fetch as a failed update.
    try{
      canonicalBuildTabs();
      canonicalRender(allItems);
      decorateNewBadges();
      if(newCount>0)playNewArticlePop();
    }catch(renderError){
      console.error('Feed downloaded successfully, but page rendering failed:',renderError);
      if(status)status.textContent=allItems.length+' stories fetched · '+newCount+' new';
      pullStatusHtml(allItems.length,false,'Feed updated · display refresh issue');
    }
    return true;
  }catch(e){
    if(status)status.textContent='Update failed';
    pullStatusHtml(allItems.length||0,true,'Unable to fetch feed');
    console.error('News feed refresh failed:',e);
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

# Add an explicit marker inside the generated page for validation/idempotence.
s2 = s2.replace('<script id="site-features-v2">', '<script id="site-features-v2">\n/* '+MARKER+' */', 1)
P.write_text(s2, encoding='utf-8')
print('Applied refresh success handling: zero-new refreshes are successful and rendering errors no longer masquerade as fetch failures.')
