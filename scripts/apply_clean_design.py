from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")
start = '<style id="clean-news-v1">'
end = '</style>'
if start in text:
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    text = before + start + after

css = '''
<style id="clean-news-v1">
/* Clean News App V1 — persistent presentation layer */
html,body{background:#fff!important;color:#111827!important}
.container{max-width:1120px!important;background:#fff!important;box-shadow:none!important}
header{background:#0b1120!important;color:#fff!important;padding:34px 28px 30px!important;border-bottom:1px solid #263244!important}
header h1{font-size:36px!important;letter-spacing:-1.8px!important;font-weight:900!important;margin-bottom:10px!important}
header p{font-size:14px!important;color:#aab4c3!important;max-width:680px!important}
.toolbar{position:static!important;padding:12px 28px!important;background:#fff!important;border-bottom:1px solid #e5e7eb!important}
.toolbar button{border-radius:6px!important;padding:8px 14px!important}
.markets{height:34px!important;background:#111827!important;border-bottom:1px solid #1f2937!important}
.tabs{position:sticky!important;top:0!important;background:#fff!important;padding:0 28px!important;gap:0!important;border-bottom:1px solid #d1d5db!important}
.tab{border:0!important;border-radius:0!important;background:transparent!important;padding:14px 13px 12px!important;color:#667085!important;font-size:11px!important;font-weight:800!important;border-bottom:3px solid transparent!important}
.tab.active{background:transparent!important;color:#111827!important;border-color:transparent transparent #7c3aed transparent!important}
.content{padding:34px 28px 46px!important}
.section-header{padding:0 0 14px!important;border-bottom:2px solid #111827!important;margin-bottom:0!important}
.section-header h2{font-size:24px!important;font-weight:850!important}
.news-item{padding:24px 0 23px!important;border-bottom:1px solid #dfe3e8!important}
.news-item h3{font-size:20px!important;line-height:1.25!important;font-weight:800!important;letter-spacing:-.35px!important;margin-bottom:8px!important}
.news-item:first-child{padding-top:28px!important}
.news-item:first-child h3{font-size:30px!important;line-height:1.15!important;letter-spacing:-.7px!important}
.description{font-size:14px!important;line-height:1.6!important;color:#4b5563!important;max-width:820px!important}
.why{background:#f7f7f9!important;border-left:3px solid #7c3aed!important;padding:10px 12px!important}
@media(max-width:600px){
header{padding:27px 18px 24px!important}
header h1{font-size:30px!important}
.toolbar{padding:10px 16px!important}
.tabs{padding:0 10px!important;overflow-x:auto!important}
.tab{padding:13px 11px 11px!important;font-size:10px!important}
.content{padding:24px 17px 34px!important}
.section-header h2{font-size:20px!important}
.news-item{padding:20px 0 19px!important}
.news-item h3{font-size:18px!important;line-height:1.3!important}
.news-item:first-child{padding-top:24px!important}
.news-item:first-child h3{font-size:25px!important;line-height:1.18!important}
.description{font-size:13px!important}
}
</style>'''

text = text.replace('</head>', css + '</head>', 1)
path.write_text(text, encoding='utf-8')
print('Applied persistent Clean News App V1 presentation layer.')
