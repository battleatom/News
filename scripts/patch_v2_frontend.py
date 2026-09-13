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
s=re.sub(r'\s*<a class="skip-link-v2"[^>]*>.*?</a>','',s,flags=re.S)
s=re.sub(r'\s*<style id="desktop-layout-fix-v1">.*?</style>','',s,flags=re.S)

if '<meta name="description"' not in s:
    s=s.replace('<title>Underreported — High-Impact News</title>','<title>Underreported — High-Impact News</title>\n<meta name="description" content="Underreported brings high-impact, local and undercovered stories together with source context and live updates.">',1)

# Keep the brand but make the masthead read like a publication instead of a dashboard.
s=re.sub(r'(<header><h1>UNDERREPORTED</h1><p>).*?(</p></header>)',r'\1The stories that matter. In one place.\2',s,count=1,flags=re.S)

# V5 presentation remains isolated from V4-derived feed/routing behavior.
# The hierarchy bridge uses explicit semantic card classes instead of the removed
# lead-story-v2 class or browser-dependent :has() selectors.
head='''\n<link rel="stylesheet" href="styles/v2.css?v=5">\n<link rel="stylesheet" href="styles/v5-visual.css?v=1" data-v5-visual="true">\n<link rel="stylesheet" href="styles/v5-hierarchy.css?v=2" data-v5-hierarchy="true">\n<script src="assets/location-v2.js?v=6"></script>\n<script src="assets/v5-hierarchy.js?v=3" defer data-v5-hierarchy="true"></script>\n'''
if '</head>' not in s:raise SystemExit('Missing </head>')
s=s.replace('</head>',head+'</head>',1)

# Always restore the body marker and skip link, including on an already-built V2 page.
body_match=re.search(r'<body([^>]*)>',s,flags=re.I)
if not body_match:raise SystemExit('Missing <body>')
attrs=body_match.group(1)
attrs=re.sub(r'\s+data-underreported-version=("[^"]*"|\'[^\']*\')','',attrs,flags=re.I)
replacement='<body'+attrs+' data-underreported-version="2"><a class="skip-link-v2" href="#news-feed">Skip to stories</a>'
s=s[:body_match.start()]+replacement+s[body_match.end():]

app='''\n<script src="assets/app-v2.js?v=3"></script>\n'''
if '</body>' not in s:raise SystemExit('Missing </body>')
s=s.replace('</body>',app+'</body>',1)

P.write_text(s,encoding='utf-8')
print('Applied Underreported V5 visual refinement: V4 behavior preserved; explicit hierarchy rails and icon badges enabled.')