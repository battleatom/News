from pathlib import Path
import re

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Theme is maintained in styles/theme.css. This script only removes legacy
# generated CSS and ensures the external stylesheet is loaded exactly once.
for marker in ('<style id="clean-news-v1">', '<style id="article-style-v1">', '<style id="load-more-style-v1">'):
    while marker in text:
        start = text.find(marker)
        end = text.find('</style>', start)
        if end == -1:
            break
        text = text[:start] + text[end + len('</style>'):]

link = '<link rel="stylesheet" href="styles/theme.css?v=2">'
text = re.sub(r'<link\s+rel=["\']stylesheet["\']\s+href=["\']styles/theme\.css(?:\?[^"\']*)?["\']\s*/?>\s*', '', text, flags=re.I)
text = text.replace('</head>', link + '\n</head>', 1)

path.write_text(text, encoding="utf-8")
print('Applied external Underreported theme from styles/theme.css.')
