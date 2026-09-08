from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Remove every previous generated design block, then insert one authoritative
# design system. All typography, colors, surfaces, spacing, and responsive
# behavior live here so later news updates cannot undo the visual theme.
marker = '<style id="clean-news-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</style>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</style>'):]

css = '''
<style id="clean-news-v1">
/* Underreported — modern Apple-inspired editorial design system. */
:root{
  color-scheme:light dark;
  --ui-font:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text",system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --ui-ink:#17181b;
  --ui-muted:#6e7077;
  --ui-subtle:#8b8d94;
  --ui-line:rgba(60,60,67,.16);
  --ui-soft:#f5f5f7;
  --ui-card:rgba(255,255,255,.88);
  --ui-page:#f5f5f7;
  --ui-header:#0b0c0f;
  --ui-header-2:#17181c;
  --ui-purple:#7c3aed;
  --ui-purple-soft:#eee7ff;
  --ui-shadow:0 18px 50px rgba(0,0,0,.09);
}
*{box-sizing:border-box}
html,body{background:var(--ui-page)!important;color:var(--ui-ink)!important;font-family:var(--ui-font)!important;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
body{letter-spacing:-.01em}
a{transition:color .16s ease,opacity .16s ease}
.container{max-width:1080px!important;background:var(--ui-card)!important;box-shadow:var(--ui-shadow)!important;border-radius:0 0 18px 18px!important;overflow:hidden!important;backdrop-filter:saturate(180%) blur(18px)!important}
header{background:linear-gradient(180deg,var(--ui-header),var(--ui-header-2))!important;color:#fff!important;padding:30px 30px 25px!important;border-bottom:1px solid rgba(255,255,255,.10)!important}
header h1{font-family:var(--ui-font)!important;font-size:30px!important;letter-spacing:-1.45px!important;line-height:1!important;font-weight:800!important;margin-bottom:8px!important}
header p{font-family:var(--ui-font)!important;font-size:12px!important;line-height:1.5!important;color:#b7bac3!important;max-width:650px!important;letter-spacing:-.01em!important}
.toolbar{position:static!important;padding:10px 25px!important;background:rgba(255,255,255,.78)!important;border-bottom:1px solid var(--ui-line)!important;gap:8px!important;backdrop-filter:blur(18px)!important}
.toolbar button{font-family:var(--ui-font)!important;border:1px solid var(--ui-line)!important;border-radius:999px!important;padding:8px 14px!important;background:rgba(255,255,255,.72)!important;color:var(--ui-ink)!important;font-size:11px!important;font-weight:650!important;box-shadow:0 1px 2px rgba(0,0,0,.04)!important}
.toolbar button:hover{background:var(--ui-soft)!important}
#status{font-size:10px!important;color:var(--ui-subtle)!important}
.markets{height:32px!important;background:#111216!important;border-bottom:1px solid rgba(255,255,255,.06)!important}
.markets-track{gap:18px!important;padding:0 18px!important;font-size:9px!important}
.tabs{position:sticky!important;top:0!important;z-index:5!important;background:rgba(250,250,252,.82)!important;backdrop-filter:saturate(180%) blur(20px)!important;padding:9px 19px!important;gap:6px!important;border-bottom:1px solid var(--ui-line)!important;box-shadow:0 2px 12px rgba(0,0,0,.05)!important;overflow-x:auto!important;scrollbar-width:none!important}
.tabs::-webkit-scrollbar{display:none}
.tab{font-family:var(--ui-font)!important;border:1px solid rgba(60,60,67,.13)!important;border-radius:999px!important;background:rgba(255,255,255,.72)!important;padding:8px 12px!important;color:#63656c!important;font-size:10px!important;font-weight:650!important;line-height:1.2!important;white-space:nowrap!important;box-shadow:0 1px 2px rgba(0,0,0,.025)!important}
.tab:hover{background:#fff!important;color:#24262b!important}
.tab.active{background:var(--ui-purple-soft)!important;color:#5b21b6!important;border-color:#d8c7ff!important;box-shadow:none!important}
.content{padding:28px 30px 42px!important}
.section-header{padding:0 0 11px!important;border-bottom:1px solid var(--ui-line)!important;margin-bottom:0!important}
.section-header h2{font-family:var(--ui-font)!important;font-size:19px!important;line-height:1.25!important;letter-spacing:-.45px!important;font-weight:750!important}
.count{font-size:9.5px!important;color:var(--ui-subtle)!important;font-weight:550!important}
.news-item{font-family:var(--ui-font)!important;background:transparent!important}
.news-item h3{font-family:var(--ui-font)!important}
.news-item h3 a{color:var(--ui-ink)!important}
.description{font-family:var(--ui-font)!important;color:#63656c!important}
.why{font-family:var(--ui-font)!important;background:rgba(124,58,237,.045)!important;border-color:rgba(124,58,237,.10)!important}
.meta{font-family:var(--ui-font)!important;color:var(--ui-subtle)!important}
.source{color:var(--ui-muted)!important;font-weight:650!important}
.load-more{font-family:var(--ui-font)!important}
footer{padding:15px!important;background:rgba(245,245,247,.72)!important;border-top:1px solid var(--ui-line)!important;font-size:9px!important}
@media(prefers-color-scheme:dark){
  :root{--ui-ink:#f5f5f7;--ui-muted:#a1a1aa;--ui-subtle:#8e8e93;--ui-line:rgba(235,235,245,.15);--ui-soft:#1c1c1e;--ui-card:rgba(28,28,30,.92);--ui-page:#0b0b0d;--ui-header:#050506;--ui-header-2:#111113;--ui-purple-soft:rgba(124,58,237,.22);--ui-shadow:0 20px 55px rgba(0,0,0,.34)}
  html,body{background:var(--ui-page)!important;color:var(--ui-ink)!important}
  .toolbar,.tabs{background:rgba(28,28,30,.78)!important}
  .toolbar button,.tab{background:rgba(44,44,46,.76)!important;color:#e5e5ea!important;border-color:var(--ui-line)!important}
  .toolbar button:hover,.tab:hover{background:#3a3a3c!important}
  .tab.active{background:var(--ui-purple-soft)!important;color:#c4a8ff!important;border-color:rgba(196,168,255,.28)!important}
  .description{color:#a1a1aa!important}
  .why{background:rgba(124,58,237,.10)!important;border-color:rgba(196,168,255,.20)!important}
  footer{background:#161618!important}
}
@media(max-width:600px){
  html,body{background:var(--ui-page)!important}
  .container{box-shadow:none!important;width:100%!important;border-radius:0!important}
  header{padding:23px 16px 20px!important}
  header h1{font-size:27px!important;letter-spacing:-1.1px!important}
  header p{font-size:11px!important}
  .toolbar{padding:8px 13px!important}
  .toolbar button{padding:8px 12px!important;font-size:10px!important}
  .markets{height:29px!important}.markets-track{gap:14px!important;padding:0 10px!important;font-size:8.5px!important}
  .tabs{padding:8px 9px!important;gap:5px!important}
  .tab{padding:8px 11px!important;font-size:9px!important}
  .content{padding:21px 15px 30px!important}
  .section-header{padding-bottom:9px!important}
  .section-header h2{font-size:18px!important}
  .news-item h3{font-size:15.5px!important;line-height:1.35!important}
  .description{font-size:11.5px!important;line-height:1.5!important}
  .why{font-size:10px!important;padding:7px 8px!important}
  .meta{font-size:8.5px!important}
}
</style>'''

text = text.replace('</head>', css + '</head>', 1)
path.write_text(text, encoding='utf-8')
print('Applied durable Apple-inspired Underreported design system.')
