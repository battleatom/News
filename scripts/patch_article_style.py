from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

marker = '<style id="article-style-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</style>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</style>'):]

css = '''
<style id="article-style-v1">
/* Equal article hierarchy with a subtle category-color rail. */
.news-item,
.news-item:first-child {
  padding:18px 13px 17px!important;
  margin:0!important;
  background:#fff!important;
  border-top:0!important;
  border-bottom:1px solid #e9ebef!important;
  border-left:4px solid var(--ui-purple)!important;
  border-radius:0!important;
}
.news-item h3,
.news-item:first-child h3 {
  font-size:16.5px!important;
  line-height:1.34!important;
  font-weight:750!important;
  letter-spacing:-.12px!important;
}
.news-item:first-child h3 { font-weight:750!important; }
.news-item:nth-child(2n) { border-left-color:#2563eb!important; }
.news-item:nth-child(3n) { border-left-color:#0f766e!important; }
.news-item:nth-child(4n) { border-left-color:#b45309!important; }
.news-item:nth-child(5n) { border-left-color:#7c3aed!important; }
.news-item:nth-child(6n) { border-left-color:#0891b2!important; }
.news-item:nth-child(7n) { border-left-color:#991b1b!important; }
@media(max-width:600px){
  .news-item,
  .news-item:first-child { padding:16px 10px 15px!important; }
  .news-item h3,
  .news-item:first-child h3 { font-size:15.5px!important; line-height:1.35!important; }
}
</style>'''

text = text.replace('</head>', css + '</head>', 1)
path.write_text(text, encoding="utf-8")
print("Applied equal article hierarchy and article color rails.")
