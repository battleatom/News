from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Remove every previous generated design block cleanly, including older
# malformed duplicate blocks, then insert exactly one presentation layer.
marker = '<style id="clean-news-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</style>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</style>'):]

css = '''
<style id="clean-news-v1">
/* Underreported Design System — deliberately visible editorial redesign */
:root{--ui-ink:#172033;--ui-muted:#667085;--ui-line:#e4e7ec;--ui-soft:#f6f7f9;--ui-purple:#7c3aed}
html,body{background:#eef0f3!important;color:var(--ui-ink)!important}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif!important;-webkit-font-smoothing:antialiased}
.container{max-width:1080px!important;background:#fff!important;box-shadow:0 0 0 1px rgba(16,24,40,.06),0 18px 55px rgba(16,24,40,.10)!important;border-radius:0 0 14px 14px!important;overflow:hidden!important}
header{background:#0b1120!important;color:#fff!important;padding:28px 30px 24px!important;border-bottom:3px solid var(--ui-purple)!important}
header h1{font-size:29px!important;letter-spacing:-1.2px!important;line-height:1!important;font-weight:850!important;margin-bottom:7px!important}
header p{font-size:12px!important;line-height:1.5!important;color:#b5bfcd!important;max-width:650px!important}
.toolbar{position:static!important;padding:9px 25px!important;background:#fff!important;border-bottom:1px solid var(--ui-line)!important;gap:8px!important}
.toolbar button{border:1px solid #d5dae2!important;border-radius:999px!important;padding:7px 13px!important;background:#fff!important;color:#172033!important;font-size:11px!important;font-weight:750!important;box-shadow:0 1px 2px rgba(16,24,40,.05)!important}
.toolbar button:hover{background:#f4f5f7!important}
#status{font-size:10px!important;color:#7a8495!important}
.markets{height:32px!important;background:#151b28!important;border-bottom:0!important}
.markets-track{gap:17px!important;padding:0 18px!important;font-size:9px!important}
.tabs{position:sticky!important;top:0!important;z-index:5!important;background:rgba(255,255,255,.97)!important;backdrop-filter:blur(12px)!important;padding:8px 19px!important;gap:6px!important;border-bottom:1px solid var(--ui-line)!important;box-shadow:0 2px 10px rgba(16,24,40,.05)!important;overflow-x:auto!important}
.tab{border:1px solid #e2e5ea!important;border-radius:999px!important;background:#fff!important;padding:7px 11px!important;color:#667085!important;font-size:10px!important;font-weight:700!important;line-height:1.2!important;white-space:nowrap!important}
.tab:hover{background:#f5f6f8!important;color:#344054!important}
.tab.active{background:#eee7ff!important;color:#5b21b6!important;border-color:#d8c7ff!important}
.content{padding:27px 30px 40px!important}
.section-header{padding:0 0 10px!important;border-bottom:2px solid #1f2937!important;margin-bottom:0!important}
.section-header h2{font-size:18px!important;line-height:1.25!important;letter-spacing:-.2px!important;font-weight:800!important}
.count{font-size:9.5px!important;color:#8a93a1!important;font-weight:650!important}
.news-item{padding:18px 3px 17px!important;border-bottom:1px solid #e9ebef!important}
.news-item h3{font-size:16.5px!important;line-height:1.34!important;font-weight:750!important;letter-spacing:-.12px!important;margin-bottom:6px!important}
.news-item h3 a{color:#172033!important}
.news-item:first-child{padding:20px 13px 19px!important;background:#faf9ff!important;border-top:1px solid #eee9fb!important;border-bottom:1px solid #ddd5f5!important;border-left:4px solid var(--ui-purple)!important;border-radius:0 10px 10px 0!important;margin:0 0 3px!important}
.news-item:first-child h3{font-size:21px!important;line-height:1.22!important;letter-spacing:-.3px!important;font-weight:800!important}
.description{font-size:12px!important;line-height:1.52!important;color:#596579!important;max-width:790px!important;margin-bottom:7px!important}
.why{font-size:10.5px!important;line-height:1.5!important;color:#4b5565!important;background:#faf9fe!important;border:1px solid #eee9fb!important;border-left:3px solid var(--ui-purple)!important;border-radius:0 8px 8px 0!important;padding:7px 9px!important;margin:8px 0!important}
.meta{font-size:9px!important;color:#98a2b3!important;gap:7px!important}
.source{color:#667085!important;font-weight:700!important}
footer{padding:14px!important;background:#fafbfc!important;border-top:1px solid var(--ui-line)!important;font-size:9px!important}
@media(max-width:600px){
html,body{background:#fff!important}
.container{box-shadow:none!important;width:100%!important;border-radius:0!important}
header{padding:23px 16px 20px!important}
header h1{font-size:26px!important;letter-spacing:-.9px!important}
header p{font-size:11px!important}
.toolbar{padding:8px 13px!important}
.toolbar button{padding:7px 11px!important;font-size:10px!important}
.markets{height:29px!important}.markets-track{gap:14px!important;padding:0 10px!important;font-size:8.5px!important}
.tabs{padding:7px 9px!important;gap:5px!important}
.tab{padding:7px 10px!important;font-size:9px!important}
.content{padding:20px 15px 28px!important}
.section-header{padding-bottom:8px!important}
.section-header h2{font-size:17px!important}
.news-item{padding:16px 0 15px!important}
.news-item:first-child{padding:17px 10px 16px!important;margin-bottom:2px!important}
.news-item h3{font-size:15.5px!important;line-height:1.35!important}
.news-item:first-child h3{font-size:20px!important;line-height:1.23!important}
.description{font-size:11.5px!important;line-height:1.5!important}
.why{font-size:10px!important;padding:7px 8px!important}
.meta{font-size:8.5px!important}
}
</style>'''

text = text.replace('</head>', css + '</head>', 1)
path.write_text(text, encoding='utf-8')
print('Applied visible Underreported editorial design system.')
