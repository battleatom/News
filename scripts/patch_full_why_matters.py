from pathlib import Path
P=Path('index.html');s=P.read_text(encoding='utf-8')
STYLE='''<style id="full-why-matters-v1">html body .news-item .v3-why-text{display:block!important;-webkit-line-clamp:unset!important;line-clamp:unset!important;overflow:visible!important;white-space:normal!important}html body .news-item .why{max-height:none!important;overflow:visible!important}</style>'''
marker='<style id="full-why-matters-v1">'
while marker in s:
 a=s.find(marker);b=s.find('</style>',a)
 if b<0:break
 s=s[:a]+s[b+8:]
if '</head>' not in s:raise SystemExit('Missing </head>')
s=s.replace('</head>',STYLE+'\n</head>',1)
P.write_text(s,encoding='utf-8')
print('Why It Matters is no longer line-clamped.')
