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
  .container{width:calc(100% - 20px)!important;max-width:none!important;margin-left:auto!important;margin-right:auto!important;overflow:hidden!important}
  header,.toolbar,.markets,.tabs,.pull-status,.content,footer,#news-feed,.section,.section-body,.news-item{min-width:0!important;max-width:100%!important}
  .content,#news-feed,.section,.section-body{width:100%!important}
  .news-item h3,.news-item h3 a,.description,.why,.meta{overflow-wrap:anywhere!important;word-break:normal!important}

  /* Desktop is a dashboard: show every navigation tab without horizontal scrolling. */
  .tabs{display:flex!important;flex-wrap:wrap!important;overflow-x:visible!important;overflow-y:visible!important;white-space:normal!important;align-items:center!important;justify-content:flex-start!important;gap:4px 5px!important;padding:8px 14px!important}
  .tab{flex:0 0 auto!important;padding:7px 10px!important;font-size:10.5px!important}

  /* Show the complete market strip on desktop instead of making it swipe horizontally. */
  .markets{height:auto!important;min-height:32px!important;overflow:visible!important;white-space:normal!important}
  .markets-track{width:100%!important;min-width:0!important;height:auto!important;min-height:32px!important;display:flex!important;flex-wrap:wrap!important;justify-content:space-between!important;align-items:center!important;gap:3px 12px!important;padding:5px 16px!important;white-space:normal!important}
  .market{flex:0 0 auto!important}
}
</style>'''
text = text.replace('</head>', desktop_fix + '\n</head>', 1)

path.write_text(text, encoding="utf-8")
print('Applied full-width desktop dashboard with fully visible tabs and markets; mobile scrolling remains unchanged.')
