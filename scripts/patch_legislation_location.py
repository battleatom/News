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
 let stateCache=null,cacheLoaded=false,cachePromise=null,lastState='';
 function stateCode(){
   let code=(localStorage.getItem('underreported-state')||'').toUpperCase();
   if(STATES[code])return code;
   const loc=(localStorage.getItem('underreported-location')||'').toUpperCase();
   const m=loc.match(/(?:,\s*|\b)([A-Z]{2})$/); return m&&STATES[m[1]]?m[1]:'NM';
 }
 function stateName(){return STATES[stateCode()]||'New Mexico'}
 function x(doc,tag,value){const e=doc.createElement(tag);e.textContent=value||'';return e}
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
 function startCacheLoad(){
   if(cacheLoaded||cachePromise)return cachePromise;
   cachePromise=fetch('state-legislation.json?ts='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('state cache unavailable');return r.json()}).then(d=>{stateCache=d;cacheLoaded=true;return d}).catch(()=>{cacheLoaded=true;stateCache=null;return null});
   return cachePromise;
 }
 function locationItems(items){
   const code=stateCode(),name=STATES[code];
   const nonLeg=items.filter(i=>(i.querySelector('category')?.textContent?.trim()||'')!=='legislation');
   const federal=items.filter(i=>(i.querySelector('category')?.textContent?.trim()||'')==='legislation' && /federal/i.test(i.querySelector('jurisdiction')?.textContent||''));
   let stateRows=[];
   if(code==='NM'){
     stateRows=items.filter(i=>(i.querySelector('category')?.textContent?.trim()||'')==='legislation' && /new mexico/i.test(i.querySelector('jurisdiction')?.textContent||''));
   }else{
     stateRows=((stateCache?.states||{})[code]?.bills||[]).map(jsonItem);
   }
   return nonLeg.concat(federal,stateRows);
 }
 function updateLabel(){
   const code=stateCode(),name=STATES[code]||'State';
   const def=CANONICAL_SECTIONS.find(x=>x[0]==='legislation');
   if(def)def[1]=`📜 Federal + ${name}`;
   if(lastState!==code){lastState=code;if(typeof canonicalBuildTabs==='function')canonicalBuildTabs();}
 }
 const previous=canonicalRender;
 canonicalRender=function(items){
   if(active!=='legislation')return previous(items);
   updateLabel();
   const code=stateCode();
   if(code!=='NM'&&!cacheLoaded){
     startCacheLoad().then(()=>{if(active==='legislation')canonicalRender(allItems)});
   }
   previous(locationItems(items));
   const sec=document.querySelector('#news-feed .section');
   if(sec){
     const intro=sec.querySelector('.x-issues-intro');
     if(intro)intro.textContent=`Federal records come from Congress.gov. State records follow your detected location (${stateName()}) and link to the official state legislature when available. News coverage is supporting context, not the primary record.`;
     const hasState=[...sec.querySelectorAll('.leg-pill')].some(p=>(p.textContent||'').includes(stateName()));
     if(!hasState&&code!=='NM'&&cacheLoaded){const n=document.createElement('div');n.className='x-issues-intro';n.textContent=`${stateName()} state records are not populated yet; federal records are shown. Configure the state legislation cache to add them.`;sec.insertBefore(n,sec.querySelector('.section-body'));}
   }
 };
 render=canonicalRender;window.render=canonicalRender;window.canonicalRender=canonicalRender;
 updateLabel();startCacheLoad();
 setInterval(updateLabel,2000);
})();
</script>'''
if '</body>' not in s: raise SystemExit('body not found')
s=s.replace('</body>',SCRIPT+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Legislation now follows detected state: Congress.gov federal + visitor state records.')
