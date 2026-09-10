from pathlib import Path
import re

P=Path('index.html')
s=P.read_text(encoding='utf-8')

# Remove prior V2 injections so this remains safe to run on every build.
s=re.sub(r'\s*<link[^>]+href="styles/v2\.css[^>]*>','',s)
s=re.sub(r'\s*<script[^>]+src="assets/location-v2\.js[^>]*></script>','',s)
s=re.sub(r'\s*<script[^>]+src="assets/app-v2\.js[^>]*></script>','',s)
s=re.sub(r'\s*<a class="skip-link-v2"[^>]*>.*?</a>','',s,flags=re.S)
s=re.sub(r'\s*<style id="desktop-layout-fix-v1">.*?</style>','',s,flags=re.S)

if '<meta name="description"' not in s:
    s=s.replace('<title>Underreported — High-Impact News</title>','<title>Underreported — High-Impact News</title>\n<meta name="description" content="Underreported brings high-impact, local and undercovered stories together with source context and live updates.">',1)

# Keep the brand but make the masthead read like a publication instead of a dashboard.
s=re.sub(r'(<header><h1>UNDERREPORTED</h1><p>).*?(</p></header>)',r'\1The stories that matter. In one place.\2',s,count=1,flags=re.S)

head='''\n<link rel="stylesheet" href="styles/v2.css?v=2">\n<script src="assets/location-v2.js?v=2"></script>\n'''
if '</head>' not in s:raise SystemExit('Missing </head>')
s=s.replace('</head>',head+'</head>',1)

if '<body>' in s:
    s=s.replace('<body>','<body data-underreported-version="2"><a class="skip-link-v2" href="#news-feed">Skip to stories</a>',1)
elif '<body ' in s and 'data-underreported-version=' not in s:
    s=s.replace('<body ','<body data-underreported-version="2" ',1)

app='''\n<script src="assets/app-v2.js?v=2"></script>\n'''
if '</body>' not in s:raise SystemExit('Missing </body>')
s=s.replace('</body>',app+'</body>',1)

P.write_text(s,encoding='utf-8')
print('Applied Underreported 2.0 final frontend layer: compact masthead, grouped navigation, story hierarchy, shared location service and health UI.')
