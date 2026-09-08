from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Remove every previous generated design block cleanly, including the older
# malformed duplicate block, then insert one current presentation layer.
marker = '<style id="clean-news-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</style>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</style>'):]

css = '''
<style id="clean-news-v1">
/* Underreported Design System — Apple editorial + Material-inspired controls */
:root{--ui-ink:#172033;--ui-muted:#667085;--ui-line:#e6e8ec;--ui-soft:#f7f8fa;--ui-purple:#7c3aed}
html,body{background:#f4f5f7!important;color:var(--ui-ink)!important}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif!important;-webkit-font-smoothing:antialiased}
.container{max-width:1120px!important;background:#fff!important;box-shadow:0 0 0 1px rgba(16,24,40,.04),0 12px 40px rgba(16,24,40,.07)!important}
header{background:#0b1120!important;color:#fff!important;padding:30px 30px 27px!important;border-bottom:1px solid #263244!important}
header h1{font-size:31px!important;letter-spacing:-1.3px!important;line-height:1!important;font-weight:850!important;margin-bottom:8px!important}
header p{font-size:12.5px!important;line-height:1.5!important;color:#aab4c3!important;max-width:650px!important}
.toolbar{position:static!important;padding:10px 26px!important;background:#fff!important;border-bottom:1px solid var(--ui-line)!important;gap:9px!important}
.toolbar button{border:1px solid #d9dde4!important;border-radius:999px!important;padding:7px 13px!important;background:#fff!important;color:#172033!important;font-size:11px!important;font-weight:750!important;box-shadow:0 1px 2px rgba(16,24,40,.04)!important}
.toolbar button:hover{background:#f7f8fa!important;border-color:#cbd0d8!important}
#status{font-size:10.5px!important;color:#7a8495!important}
.markets{height:33px!important;background:#151b28!important;border-bottom:0!important}
.markets-track{gap:17px!important;padding:0 18px!important;font-size:9.5px!important}
.tabs{position:sticky!important;top:0!important;background:rgba(255,255,255,.96)!important;backdrop-filter:blur(10px)!important;padding:7px 20px!important;gap:6px!important;border-bottom:1px solid var(--ui-line)!important;box-shadow:0 2px 8px rgba(16,24,40,.035)!important}
.tab{border:1px solid transparent!important;border-radius:999px!important;background:transparent!important;padding:7px 11px!important;color:#667085!important;font-size:10.5px!important;font-weight:700!important;line-height:1.2!important}
.tab:hover{background:#f4f5f7!important;color:#344054!important}
.tab.active{background:#f0eafd!important;color:#5b21b6!important;border-color:#e5d9ff!important}
.content{padding:28px 30px 42px!important}
.section-header{padding:0 0 11px!important;border-bottom:1px solid #d7dbe2!important;margin-bottom:0!important}
.section-header h2{font-size:19px!important;line-height:1.25!important;letter-spacing:-.25px!important;font-weight:800!important}
.count{font-size:10px!important;color:#8a93a1!important;font-weight:650!important}
.news-item{padding:19px 2px 18px!important;border-bottom:1px solid #eceef1!important}
.news-item h3{font-size:17px!important;line-height:1.34!important;font-weight:750!important;letter-spacing:-.15px!important;margin-bottom:6px!important}
.news-item h3 a{color:#172033!important}
.news-item:first-child{padding-top:21px!important}
.news-item:first-child h3{font-size:23px!important;line-height:1.2!important;letter-spacing:-.45px!important;font-weight:800!important}
.description{font-size:12.5px!important;line-height:1.55!important;color:#596579!important;max-width:790px!important;margin-bottom:8px!important}
.why{font-size:11px!important;line-height:1.5!important;color:#4b5565!important;background:#faf9fe!important;border:1px solid #eee9fb!important;border-left:3px solid var(--ui-purple)!important;border-radius:0 9px 9px 0!important;padding:8px 10px!important;margin:9px 0!important}
.meta{font-size:9.5px!important;color:#98a2b3!important;gap:7px!important}
.source{color:#667085!important;font-weight:700!important}
footer{padding:15px!important;background:#fafbfc!important;border-top:1px solid var(--ui-line)!important;font-size:9.5px!important}
@media(max-width:600px){
html,body{background:#fff!important}
.container{box-shadow:none!important;width:100%!important}
header{padding:25px 17px 22px!important}
header h1{font-size:27px!important;letter-spacing:-1px!important;margin-bottom:7px!important}
header p{font-size:11.5px!important}
.toolbar{padding:9px 14px!important}
.toolbar button{padding:7px 12px!important;font-size:10.5px!important}
.markets{height:30px!important}.markets-track{gap:14px!important;padding:0 11px!important;font-size:9px!important}
.tabs{padding:7px 9px!important;gap:5px!important}
.tab{padding:7px 10px!important;font-size:9.5px!important}
.content{padding:22px 16px 30px!important}
.section-header{padding-bottom:9px!important}
.section-header h2{font-size:18px!important}
.news-item{padding:17px 0 16px!important}
.news-item h3{font-size:16px!important;line-height:1.34!important;font-weight:750!important}
.news-item:first-child{padding-top:19px!important}
.news-item:first-child h3{font-size:21px!important;line-height:1.22!important}
.description{font-size:12px!important;line-height:1.52!important}
.why{font-size:10.5px!important;padding:8px 9px!important}
.meta{font-size:9px!important}
}
</style>'''

text = text.replace('</head>', css + '</head>', 1)
path.write_text(text, encoding='utf-8')
print('Applied refined Underreported Design System.')
