from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Theme is maintained in styles/theme.css. Remove legacy generated style blocks
# and ensure the single external theme stylesheet is present exactly once.
for marker in ('<style id="clean-news-v1">', '<style id="article-style-v1">', '<style id="load-more-style-v1">'):
    while marker in text:
        start = text.find(marker)
        end = text.find('</style>', start)
        if end == -1:
            break
        text = text[:start] + text[end + len('</style>'):]

link = '<link rel="stylesheet" href="styles/theme.css?v=1">'
if link not in text:
    text = text.replace('</head>', link + '\n</head>', 1)

path.write_text(text, encoding='utf-8')
print('Theme source of truth: styles/theme.css')
