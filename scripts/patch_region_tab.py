from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Make the new tab visible without changing the existing Local / Four Corners tab.
old_sections = "const sections=[['top','🔴 Top Stories','#dc2626'],['underreported','🟣 Underreported','#7c3aed'],['world','🌎 World','#2563eb'],['us','🇺🇸 United States','#1e3a8a'],['presidential','🏛️ Presidential','#b45309'],['federal','🏛️ Federal Government','#ca8a04'],['nm','🏜️ New Mexico','#0f766e'],['local','📍 Local / Four Corners','#15803d'],['technology','💻 Technology','#0891b2'],['gaming','🎮 Gaming & Computing','#7c3aed'],['military','⚔️ Military & War','#991b1b']];"
new_sections = "const sections=[['top','🔴 Top Stories','#dc2626'],['underreported','🟣 Underreported','#7c3aed'],['world','🌎 World','#2563eb'],['us','🇺🇸 United States','#1e3a8a'],['presidential','🏛️ Presidential','#b45309'],['federal','🏛️ Federal Government','#ca8a04'],['nm','🏜️ New Mexico','#0f766e'],['local','📍 Local / Four Corners','#15803d'],['region','🌎 Region','#2563eb'],['technology','💻 Technology','#0891b2'],['gaming','🎮 Gaming & Computing','#7c3aed'],['military','⚔️ Military & War','#991b1b']];"
if old_sections in text:
    text = text.replace(old_sections, new_sections, 1)

# Append a small override layer rather than rewriting the existing news renderer.
# This preserves the current Local tab and all existing category behavior.
marker = '<script id="region-tab-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</script>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</script>'):]

script = r'''<script id="region-tab-v1">
let detectedRegion = localStorage.getItem('underreported-region') || 'southwest';
let detectedLocation = localStorage.getItem('underreported-location') || '';
const regionLabels = {
  southwest:'Southwest', west:'West', mountain:'Mountain West', midwest:'Midwest',
  south:'South', northeast:'Northeast', 'pacific-northwest':'Pacific Northwest', southeast:'Southeast'
};
const stateRegion = {
  AZ:'southwest', NM:'southwest', UT:'southwest', CO:'southwest',
  CA:'west', NV:'west',
  ID:'mountain', MT:'mountain', WY:'mountain',
  IL:'midwest', IN:'midwest', MI:'midwest', OH:'midwest', WI:'midwest', MN:'midwest', IA:'midwest', MO:'midwest', KS:'midwest', NE:'midwest', SD:'midwest', ND:'midwest',
  TX:'south', OK:'south', AR:'south', LA:'south', TN:'south', KY:'south', VA:'south', WV:'south', MD:'south', DE:'south',
  NY:'northeast', PA:'northeast', NJ:'northeast', CT:'northeast', RI:'northeast', MA:'northeast', VT:'northeast', NH:'northeast', ME:'northeast',
  WA:'pacific-northwest', OR:'pacific-northwest', AK:'pacific-northwest',
  FL:'southeast', GA:'southeast', AL:'southeast', SC:'southeast', NC:'southeast', MS:'southeast'
};

function regionRender(items){
  const def=sections.find(x=>x[0]===active);
  const accent=def?def[2]:'#111827';
  let list=items.filter(item=>(item.querySelector('category')?.textContent?.trim()||'world')===active);
  if(active==='region') list=list.filter(item=>(item.querySelector('region')?.textContent?.trim()||'')===detectedRegion);
  const root=document.getElementById('news-feed');root.innerHTML='';
  const sec=document.createElement('section');sec.className='section';sec.style.setProperty('--accent',accent);
  const head=document.createElement('div');head.className='section-header';
  const label=active==='region' ? '🌎 '+regionLabels[detectedRegion]+' Region' : (def?def[1]:'News');
  const locationNote=active==='region' && detectedLocation ? ' · '+detectedLocation : '';
  head.innerHTML=`<h2>${esc(label)}</h2><span class="count">${list.length} stories${esc(locationNote)}</span>`;sec.appendChild(head);
  const body=document.createElement('div');body.className='section-body';
  if(!list.length) body.innerHTML='<div class="empty">No regional stories available right now.</div>';
  list.forEach((item,i)=>{
    const title=item.querySelector('title')?.textContent||'Untitled';
    const desc=item.querySelector('description')?.textContent||'';
    const why=item.querySelector('whyMatters')?.textContent||'';
    const link=item.querySelector('link')?.textContent||'#';
    const date=item.querySelector('pubDate')?.textContent||'';
    const source=item.querySelector('source')?.textContent||'';
    const article=document.createElement('article');article.className='news-item';
    article.innerHTML=`<h3><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(title)}</a></h3>${desc?`<p class="description">${esc(desc)}</p>`:''}${why?`<div class="why">${esc(why)}</div>`:''}<div class="meta"><span>${esc(formatDate(date))}</span>${source?`<span class="source">${esc(source)}</span>`:''}</div>`;
    body.appendChild(article);
  });
  sec.appendChild(body);root.appendChild(sec);
}

// Replace the existing renderer with one that understands the new region metadata.
render = regionRender;

// Keep the existing tab persistence, but detect the user's region when Region is selected.
const originalBuildTabs = buildTabs;
buildTabs = function(){
  const tabs=document.getElementById('tabs');tabs.innerHTML='';
  sections.forEach(([key,label,accent])=>{
    const b=document.createElement('button');b.className='tab'+(key===active?' active':'');
    b.textContent=key==='region' && detectedLocation ? '🌎 '+regionLabels[detectedRegion] : label;
    b.onclick=async()=>{
      active=key;localStorage.setItem('underreported-active-tab',active);buildTabs();
      if(key==='region') await detectUserRegion();
      render(allItems);
    };
    b.style.setProperty('--accent',accent);tabs.appendChild(b);
  });
};

async function detectUserRegion(){
  try{
    let coords;
    if(navigator.geolocation){
      coords=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:8000,maximumAge:300000}));
      coords={latitude:coords.coords.latitude,longitude:coords.coords.longitude};
    }
    const params=new URLSearchParams({localityLanguage:'en'});
    if(coords){params.set('latitude',String(coords.latitude));params.set('longitude',String(coords.longitude));}
    const response=await fetch('https://api.bigdatacloud.net/data/reverse-geocode-client?'+params.toString(),{cache:'no-store'});
    if(!response.ok)throw new Error('Location lookup failed');
    const data=await response.json();
    const code=(data.principalSubdivisionCode||'').replace(/^US-/,'').toUpperCase();
    if(stateRegion[code]) detectedRegion=stateRegion[code];
    detectedLocation=[data.city,data.principalSubdivisionCode?.replace(/^US-/,'')].filter(Boolean).join(', ');
    localStorage.setItem('underreported-region',detectedRegion);
    localStorage.setItem('underreported-location',detectedLocation);
    buildTabs();
  }catch(e){
    // Keep the last successful region; default to Southwest for first-time users.
    buildTabs();
  }
}

// Detect quietly in the background so the Regional tab is ready when opened.
detectUserRegion();
</script>'''
text = text.replace('</body>', script + '</body>', 1)
path.write_text(text, encoding='utf-8')
print('Added location-aware Regional tab without changing Local / Four Corners.')
'''
path.write_text(text, encoding='utf-8')
print('Added location-aware Regional tab without changing Local / Four Corners.')
