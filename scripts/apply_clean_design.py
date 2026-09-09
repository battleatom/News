from pathlib import Path
import re

path = Path("index.html")
text = path.read_text(encoding="utf-8")

for marker in ('<style id="clean-news-v1">', '<style id="article-style-v1">', '<style id="load-more-style-v1">', '<style id="desktop-layout-fix-v1">'):
    while marker in text:
        start = text.find(marker)
        end = text.find('</style>', start)
        if end == -1:
            break
        text = text[:start] + text[end + len('</style>'):]

legacy_start = text.find('<style>\n:root{--ink:#101828;')
if legacy_start != -1:
    legacy_end = text.find('</style>', legacy_start)
    if legacy_end != -1:
        text = text[:legacy_start] + text[legacy_end + len('</style>'):]

for href in ('styles/theme.css', 'styles/header.css'):
    text = re.sub(r'<link\s+rel=["\']stylesheet["\']\s+href=["\']' + re.escape(href) + r'(?:\?[^"\']*)?["\']\s*/?>\s*', '', text, flags=re.I)

links = '<link rel="stylesheet" href="styles/theme.css?v=3">\n<link rel="stylesheet" href="styles/header.css?v=4">'
text = text.replace('</head>', links + '\n</head>', 1)

desktop_fix = r'''<style id="desktop-layout-fix-v1">
@media (min-width:601px){
  html,body{width:100%!important;max-width:100%!important;overflow-x:hidden!important}
  body{padding:10px!important}
  .container{width:calc(100% - 20px)!important;max-width:1060px!important;margin-left:auto!important;margin-right:auto!important;overflow:hidden!important}
  header,.toolbar,.markets,.tabs,.pull-status,.content,footer,#news-feed,.section,.section-body,.news-item{min-width:0!important;max-width:100%!important}
  .content,#news-feed,.section,.section-body{width:100%!important}
  .news-item h3,.news-item h3 a,.description,.why,.meta{overflow-wrap:anywhere!important;word-break:normal!important}
}
</style>'''
text = text.replace('</head>', desktop_fix + '\n</head>', 1)

path.write_text(text, encoding="utf-8")
print('Applied authoritative Underreported theme, newspaper header styles, and desktop width containment.')
