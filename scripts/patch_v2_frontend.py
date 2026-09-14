from pathlib import Path
import hashlib
import re

ROOT=Path('.')
P=Path('index.html')
s=P.read_text(encoding='utf-8')

ASSETS={
    'styles/v2.css':'style',
    'styles/v5-visual.css':'style',
    'styles/card-feedback.css':'style',
    'assets/location-v2.js':'script',
    'assets/v3-ui.js':'script',
    'assets/app-v2.js':'script',
    'assets/card-feedback.js':'script',
}

def version(path: str) -> str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha256(data).hexdigest()[:12]

# Remove prior frontend injections so this remains safe to run on every build.
for path,kind in ASSETS.items():
    escaped=re.escape(path)
    if kind=='style':
        s=re.sub(r'\s*<link[^>]+href=["\']'+escaped+r'(?:\?[^"\']*)?["\'][^>]*>','',s,flags=re.I)
    else:
        s=re.sub(r'\s*<script[^>]+src=["\']'+escaped+r'(?:\?[^"\']*)?["\'][^>]*></script>','',s,flags=re.I)
s=re.sub(r'\s*<a class="skip-link-v2"[^>]*>.*?</a>','',s,flags=re.S)
s=re.sub(r'\s*<style id="desktop-layout-fix-v1">.*?</style>','',s,flags=re.S)

if '<meta name="description"' not in s:
    s=s.replace('<title>Underreported — High-Impact News</title>','<title>Underreported — High-Impact News</title>\n<meta name="description" content="Underreported brings high-impact, local and undercovered stories together with source context and live updates.">',1)

s=re.sub(r'(<header><h1>UNDERREPORTED</h1><p>).*?(</p></header>)',r'\1The stories that matter. In one place.\2',s,count=1,flags=re.S)

head='''
<link rel="stylesheet" href="styles/v2.css?v={v2}">
<link rel="stylesheet" href="styles/v5-visual.css?v={visual}" data-v5-visual="true">
<link rel="stylesheet" href="styles/card-feedback.css?v={feedback_style}" data-card-feedback-style="true">
<script src="assets/location-v2.js?v={location}" defer></script>
<script src="assets/v3-ui.js?v={presentation}" defer></script>
'''.format(
    v2=version('styles/v2.css'),
    visual=version('styles/v5-visual.css'),
    feedback_style=version('styles/card-feedback.css'),
    location=version('assets/location-v2.js'),
    presentation=version('assets/v3-ui.js'),
)
if '</head>' not in s:raise SystemExit('Missing </head>')
s=s.replace('</head>',head+'</head>',1)

body_match=re.search(r'<body([^>]*)>',s,flags=re.I)
if not body_match:raise SystemExit('Missing <body>')
attrs=body_match.group(1)
attrs=re.sub(r'\s+data-underreported-version=("[^"]*"|\'[^\']*\')','',attrs,flags=re.I)
replacement='<body'+attrs+' data-underreported-version="5"><a class="skip-link-v2" href="#news-feed">Skip to stories</a>'
s=s[:body_match.start()]+replacement+s[body_match.end():]

app='''
<script src="assets/app-v2.js?v={app}"></script>
<script src="assets/card-feedback.js?v={feedback}" data-card-feedback-script="true"></script>
'''.format(
    app=version('assets/app-v2.js'),
    feedback=version('assets/card-feedback.js'),
)
if '</body>' not in s:raise SystemExit('Missing </body>')
s=s.replace('</body>',app+'</body>',1)

P.write_text(s,encoding='utf-8')
print('Applied Underreported V5 frontend with content-hashed assets, feedback controls, and explicit ownership.')