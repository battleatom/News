from pathlib import Path

P=Path('index.html')
s=P.read_text(encoding='utf-8')
marker='<style id="why-matters-full-v1">'
while marker in s:
    a=s.find(marker); b=s.find('</style>',a)
    if b<0: break
    s=s[:a]+s[b+8:]
STYLE='''<style id="why-matters-full-v1">
#news-feed .news-item .why{max-height:none!important;overflow:visible!important;display:block!important;white-space:normal!important}
#news-feed .news-item .why .v3-why-text{display:block!important;max-height:none!important;overflow:visible!important;-webkit-line-clamp:unset!important;line-clamp:unset!important;-webkit-box-orient:initial!important;white-space:normal!important;text-overflow:clip!important}
</style>'''
if '</head>' not in s: raise SystemExit('Missing </head>')
s=s.replace('</head>',STYLE+'\n</head>',1)
P.write_text(s,encoding='utf-8')
print('Why It Matters text is fully visible; two-line clamp removed.')
