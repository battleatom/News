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

path.write_text(text, encoding="utf-8")
print('Removed legacy article CSS; visual styling is controlled by styles/theme.css.')
