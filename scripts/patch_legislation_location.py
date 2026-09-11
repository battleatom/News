from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')
marker='<script id="legislation-location-v1">'
while marker in s:
    a=s.find(marker); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]

SCRIPT=r'''<script id="legislation-location-v1">
(function(){
 'use strict';
 const STATES={AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',DC:'District of Columbia'};
 const LEGISLATIVE_TERMS=['bill','legislation','legislature','law','lawsuit','regulation','rule','governor','state senate','state house','general assembly','capitol','veto','signed','ordinance','budget'];
 let stateCache=null,cacheLoaded=false,cachePromise=null,lastState='';
 function stateCode(){
   let code=(localStorage.getItem('underreported-state')||'').toUpperCase();
   if(STATES[code])return code;
   const loc=(localStorage.getItem('underreported-location')||'').toUpperCase();
   const m=loc.match(/(?:,\s*|\b)([A-Z]{2})$/); return m&&STATES[m[1]]?m[1]:'NM';
 }
 function stateName(){return STATES[stateCode()]||'New Mexico'}
 function x(doc,tag,value){const e=doc.createElement(tag);e.textContent=value||'';return e}
 function itemText(item){return `${item.querySelector('title')?.textContent||''} ${item.querySelector('description')?.textContent||''} ${item.querySelector('source')?.textContent||''}`.toLowerCase()}
 function itemKey(item){return (item.querySelector('link')?.textContent||item.querySelector('title')?.textContent||'').trim().toLowerCase()}
 function matchesState(item,code,name){
   const tagged=(item.querySelector('state')?.textContent||'').trim().toLowerCase();
   if(tagged)return tagged===code.toLowerCase()||tagged===name.toLowerCase();
   return itemText(item).includes(name.toLowerCase());
 }
 function jsonItem(rec){
   const doc=document.implementation.createDocument('','item'); const item=doc.documentElement;
   const link=rec.officialSource||rec.indexSource||'#';
   item.appendChild(x(doc,'title',`${rec.billNumber||''} — ${rec.title||'State legislation'}`));
   item.appendChild(x(doc,'link',link)); item.appendChild(x(doc,'description',rec.description||rec.title||''));
   item.appendChild(x(doc,'pubDate',rec.latestActionDate||rec.statusDate||'')); item.appendChild(x(doc,'source',`${rec.stateName||stateName()} Legislature`));
   item.appendChild(x(doc,'category','legislation')); item.appendChild(x(doc,'jurisdiction',rec.stateName||stateName()));
   item.appendChild(x(doc,'status',rec.status||'Active')); item.appendChild(x(doc,'whatItDoes',rec.description||rec.title||''));
   item.appendChild(x(doc,'whoAffected','Residents, organizations, agencies, or programs covered by the measure'));
   item.appendChild(x(doc,'effectiveDate','See official bill text / enacted law'));
   item.appendChild(x(doc,'nextStep',/passed|enrolled/i.test(rec.status||'')?'Implementation, executive action, or final procedural steps.':'Watch the next committee, floor, or executive action.'));
   item.appendChild(x(doc,'officialSource',rec.officialSource||'')); item.appendChild(x(doc,'billNumber',rec.billNumber||''));
   item.appendChild(x(doc,'latestAction',rec.latestAction||'')); item.appendChild(x(doc,'sponsor',rec.sponsor||''));
   return item;
 }
 function coverageItem(src,name){
   const doc=document.implementation.createDocument('','item');const item=doc.documentElement;
   const title=src.querySelector('title')?.textContent||'State government update';
   const link=src.querySelector('link')?.textContent||'#';const desc=src.querySelector('description')?.textContent||'';
   const date=src.querySelector('pubDate')?.textContent||'';const source=src.querySelector('source')?.textContent||'News coverage';
   item.appendChild(x(doc,'title',title));item.appendChild(x(doc,'link',link));item.appendChild(x(doc,'description',desc));
   item.appendChild(x(doc,'pubDate',date));item.appendChild(x(doc,'source',source));item.appendChild(x(doc,'category','legislation'));
   item.appendChild(x(doc,'jurisdiction',`${name} · news coverage`));item.appendChild(x(doc,'status','Supporting coverage'));
   item.appendChild(x(doc,'whatItDoes',desc||title));item.appendChild(x(doc,'whoAffected',`${name} residents, agencies, businesses, or programs affected by the reported action`));
   item.appendChild(x(doc,'effectiveDate','See the official state record for controlling dates'));item.appendChild(x(doc,'nextStep',`Follow the ${name} legislature or agency for the next official action.`));
   return item;
 }
 function startCacheLoad(){
   if(cacheLoaded||cachePromise)return cachePromise;
   cachePromise=fetch('state-legislation.json?ts='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('state cache unavailable');return r.json()}).then(d=>{stateCache=d;cacheLoaded=true;return d}).catch(()=>{cacheLoaded=true;stateCache=null;return null});
   return cachePromise;
 }
 function stateCoverage(items,code,name){
   const candidates=items.filter(i=>['region','nm','us','top'].includes((i.querySelector('category')?.textContent||'').trim())&&matchesState(i,code,name));
   const priority=candidates.filter(i=>LEGISLATIVE_TERMS.some(term=>itemText(i).includes(term)));
   const ordered=[...priority,...candidates.filter(i=>!priority.includes(i))].sort((a,b)=>(Date.parse(b.querySelector('pubDate')?.textContent||'')||0)-(Date.parse(a.querySelector('pubDate')?.textContent||'')||0));
   const seen=new Set(),out=[];
   for(const src of ordered){const k=itemKey(src);if(!k||seen.has(k))continue;seen.add(k);out.push(coverageItem(src,name));if(out.length>=18)break;}
   return out;
 }
 function locationItems(items){
   const code=stateCode(),name=STATES[code]||'State';
   const nonLeg=items.filter(i=>(i.querySelector('category')?.textContent?.trim()||'')!=='legislation');
   const federal=items.filter(i=>(i.querySelector('category')?.textContent?.trim()||'')==='legislation' && /federal/i.test(i.querySelector('jurisdiction')?.textContent||''));
   let stateRows=[];
   if(code==='NM'){
     stateRows=items.filter(i=>(i.querySelector('category')?.textContent?.trim()||'')==='legislation' && /new mexico/i.test(i.querySelector('jurisdiction')?.textContent||''));
   }else{
     stateRows=((stateCache?.states||{})[code]?.bills||[]).map(jsonItem);
   }
   if(stateRows.length<10){
     const seen=new Set(stateRows.map(itemKey));
     for(const row of stateCoverage(items,code,name)){const k=itemKey(row);if(!k||seen.has(k))continue;seen.add(k);stateRows.push(row);if(stateRows.length>=18)break;}
   }
   return nonLeg.concat(federal,stateRows);
 }
 function updateLabel(){
   const code=stateCode(),name=STATES[code]||'State';
   const def=CANONICAL_SECTIONS.find(x=>x[0]==='legislation');
   if(def)def[1]=`📜 Federal + ${name}`;
   if(lastState!==code){lastState=code;if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();}
 }

 window.__categoryRenderers=window.__categoryRenderers||{};
 const baseLegislationRenderer=window.__categoryRenderers.legislation;
 if(typeof baseLegislationRenderer!=='function')throw new Error('Legislation category renderer missing before location patch');
 window.__categoryRenderers.legislation=function(items){
   updateLabel();
   const code=stateCode();
   if(code!=='NM'&&!cacheLoaded)startCacheLoad().then(()=>{if(active==='legislation')canonicalRender(allItems)});
   baseLegislationRenderer(locationItems(items));
   const sec=document.querySelector('#news-feed .section');
   if(sec){
     const intro=sec.querySelector('.x-issues-intro');
     if(intro)intro.textContent=`Federal records come from Congress.gov. ${stateName()} follows your detected location. Official state records are used when available; otherwise established state news coverage is clearly labeled as supporting coverage.`;
   }
 };

 updateLabel();startCacheLoad();
 window.addEventListener('underreported:location',()=>{updateLabel();if(active==='legislation')canonicalRender(allItems)});
})();
</script>'''
if '</body>' not in s: raise SystemExit('body not found')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Legislation location now extends the registered category renderer without wrapping canonicalRender.')
