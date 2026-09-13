from pathlib import Path
import re

P=Path('index.html')
s=P.read_text(encoding='utf-8')

# Remove prior frontend injections so this remains safe to run on every build.
s=re.sub(r'\s*<link[^>]+href="styles/v2\.css[^>]*>','',s)
s=re.sub(r'\s*<link[^>]+href="styles/v5-visual\.css[^>]*>','',s)
s=re.sub(r'\s*<link[^>]+href="styles/v5-hierarchy\.css[^>]*>','',s)
s=re.sub(r'\s*<script[^>]+src="assets/location-v2\.js[^>]*></script>','',s)
s=re.sub(r'\s*<script[^>]+src="assets/v5-hierarchy\.js[^>]*></script>','',s)
s=re.sub(r'\s*<script[^>]+src="assets/app-v2\.js[^>]*></script>','',s)
s=re.sub(r'\s*<style id="v5-hierarchy-critical-v1">.*?</style>','',s,flags=re.S)
s=re.sub(r'\s*<script id="v5-hierarchy-bootstrap-v1">.*?</script>','',s,flags=re.S)
s=re.sub(r'\s*<a class="skip-link-v2"[^>]*>.*?</a>','',s,flags=re.S)
s=re.sub(r'\s*<style id="desktop-layout-fix-v1">.*?</style>','',s,flags=re.S)

if '<meta name="description"' not in s:
    s=s.replace('<title>Underreported — High-Impact News</title>','<title>Underreported — High-Impact News</title>\n<meta name="description" content="Underreported brings high-impact, local and undercovered stories together with source context and live updates.">',1)

# Keep the brand but make the masthead read like a publication instead of a dashboard.
s=re.sub(r'(<header><h1>UNDERREPORTED</h1><p>).*?(</p></header>)',r'\1The stories that matter. In one place.\2',s,count=1,flags=re.S)

# V5 presentation remains isolated from V4-derived feed/routing behavior.
# Normal card CSS loads first. The hierarchy sheet follows it, then an inline
# critical subset guarantees the rail/icon contract survives cache/CDN issues.
critical='''
<style id="v5-hierarchy-critical-v1">
html body .news-item[data-hierarchy="high"]:not(.nfl-game-card),html body .news-item.v5-hierarchy-high:not(.nfl-game-card){border-left:5px solid #dc2626!important}
html body .news-item[data-hierarchy="analysis"]:not(.nfl-game-card),html body .news-item.v5-hierarchy-analysis:not(.nfl-game-card){border-left:5px solid #7c3aed!important}
html body .news-item[data-hierarchy="local"]:not(.nfl-game-card),html body .news-item.v5-hierarchy-local:not(.nfl-game-card){border-left:5px solid #15803d!important}
html body .news-item[data-hierarchy="trending"]:not(.nfl-game-card),html body .news-item.v5-hierarchy-trending:not(.nfl-game-card){border-left:5px solid #2563eb!important}
html body .news-item[data-hierarchy="standard"]:not(.nfl-game-card),html body .news-item.v5-hierarchy-standard:not(.nfl-game-card){border-left:3px solid #64748b!important}
html body .v3-importance{display:inline-flex!important;align-items:center!important;gap:4px!important;position:relative!important;visibility:visible!important;opacity:1!important}
html body .v3-importance.high::before{content:'⚡'}
html body .v3-importance.analysis::before{content:'◆'}
html body .v3-importance.local::before{content:'●'}
html body .v3-importance.trending::before{content:'↗'}
html body .v3-importance.standard::before{content:'•'}
html body .nfl-game-card .v3-importance{display:none!important}
</style>
'''
head=f'''\n<link rel="stylesheet" href="styles/v2.css?v=5">\n<link rel="stylesheet" href="styles/v5-visual.css?v=1" data-v5-visual="true">\n<link id="v5-hierarchy-style" rel="stylesheet" href="styles/v5-hierarchy.css?v=3" data-v5-hierarchy="true">\n{critical}<script src="assets/location-v2.js?v=7"></script>\n<script src="assets/v5-hierarchy.js?v=4" defer data-v5-hierarchy="true" data-underreported-v5-hierarchy="true"></script>\n'''
if '</head>' not in s:raise SystemExit('Missing </head>')
s=s.replace('</head>',head+'</head>',1)

# Always restore the body marker and skip link, including on an already-built V2 page.
body_match=re.search(r'<body([^>]*)>',s,flags=re.I)
if not body_match:raise SystemExit('Missing <body>')
attrs=body_match.group(1)
attrs=re.sub(r'\s+data-underreported-version=("[^"]*"|\'[^\']*\')','',attrs,flags=re.I)
replacement='<body'+attrs+' data-underreported-version="2"><a class="skip-link-v2" href="#news-feed">Skip to stories</a>'
s=s[:body_match.start()]+replacement+s[body_match.end():]

# Final inline bootstrap is intentionally self-contained. It runs after the page's
# renderers/app script and does not depend on a cached external hierarchy asset.
# This makes hierarchy attachment a last-mile invariant of every rendered card.
bootstrap='''
<script id="v5-hierarchy-bootstrap-v1">
(function(){
 'use strict';
 if(window.__v5HierarchyBootstrapV1)return;
 window.__v5HierarchyBootstrapV1=true;
 const classes=['v5-hierarchy-high','v5-hierarchy-analysis','v5-hierarchy-local','v5-hierarchy-trending','v5-hierarchy-standard'];
 const local=new Set(['nm','local','region']);
 const highFirst=new Set(['top','world','us','presidential','federal','military']);
 const labels={high:'HIGH IMPACT',analysis:'ANALYSIS',local:'LOCAL',trending:'TRENDING',standard:'STANDARD'};
 function sectionFor(card){
   const bound=card?.dataset?.section||card?.closest?.('.section')?.dataset?.section||'';
   if(bound)return bound;
   try{if(typeof active!=='undefined'&&active)return String(active)}catch(e){}
   const selected=document.querySelector('#tabs .tab.active')?.textContent||'';
   const text=selected.toLowerCase();
   if(text.includes('world'))return 'world';if(text.includes('united states'))return 'us';if(text.includes('presidential'))return 'presidential';if(text.includes('federal'))return 'federal';if(text.includes('new mexico'))return 'nm';if(text.includes('local'))return 'local';if(text.includes('region'))return 'region';if(text.includes('technology'))return 'technology';if(text.includes('gaming'))return 'gaming';if(text.includes('military'))return 'military';if(text.includes('entertainment'))return 'entertainment';if(text.includes('underreported'))return 'underreported';if(text.includes('top issues'))return 'x';if(text.includes('top stories'))return 'top';
   return '';
 }
 function kindFor(card,index,section){
   if(card.classList.contains('nfl-game-card'))return '';
   const bound=card.dataset.hierarchy||card.dataset.v5Hierarchy||'';
   if(bound)return bound;
   if(card.classList.contains('underreported-item')||section==='underreported')return 'analysis';
   if(card.classList.contains('x-issue-item')||section==='x')return 'trending';
   if(local.has(section))return 'local';
   if(index===0&&highFirst.has(section))return 'high';
   return 'standard';
 }
 function apply(){
   const cards=[...document.querySelectorAll('#news-feed .news-item')];
   cards.forEach((card,index)=>{
     const section=sectionFor(card),kind=kindFor(card,index,section);
     if(!kind)return;
     const wanted='v5-hierarchy-'+kind;
     classes.forEach(c=>{if(c!==wanted)card.classList.remove(c)});
     card.classList.add(wanted);card.dataset.hierarchy=kind;card.dataset.v5Hierarchy=kind;if(section)card.dataset.section=section;
     let badge=card.querySelector(':scope > .v3-importance');
     if(!badge){badge=document.createElement('span');card.prepend(badge)}
     badge.className='v3-importance '+kind;badge.dataset.v5HierarchyBadge=kind;
     if(badge.textContent!==labels[kind])badge.textContent=labels[kind];
   });
   document.body?.setAttribute('data-v5-hierarchy-bootstrap','active');
 }
 let queued=false;
 function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;apply()})}
 function start(){
   apply();
   const feed=document.getElementById('news-feed');
   if(feed)new MutationObserver(ms=>{if(ms.some(m=>[...m.addedNodes].some(n=>n.nodeType===1&&(n.matches?.('.news-item')||n.querySelector?.('.news-item')))))queue()}).observe(feed,{childList:true,subtree:true});
   document.addEventListener('underreported:feed-rendered',queue);
   document.getElementById('tabs')?.addEventListener('click',()=>requestAnimationFrame(queue),true);
   window.addEventListener('underreported:location',queue,{passive:true});
   setTimeout(apply,250);setTimeout(apply,1000);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
</script>
'''
app='''\n<script src="assets/app-v2.js?v=3"></script>\n'''+bootstrap
if '</body>' not in s:raise SystemExit('Missing </body>')
s=s.replace('</body>',app+'</body>',1)

P.write_text(s,encoding='utf-8')
print('Applied Underreported V5 visual refinement: persistent inline hierarchy rails/icons plus render-bound metadata enabled.')
