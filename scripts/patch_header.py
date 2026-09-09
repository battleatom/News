from pathlib import Path
import re

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# The newspaper treatment belongs to the single page-level <header> only.
# Keep it as an external stylesheet so the generated feed cannot duplicate it.
link = '<link rel="stylesheet" href="styles/header.css?v=1">'
text = re.sub(
    r'<link\s+rel=["\']stylesheet["\']\s+href=["\']styles/header\.css(?:\?[^"\']*)?["\']\s*/?>\s*',
    '', text, flags=re.I,
)
text = text.replace('</head>', link + '\n</head>', 1)

# Remove any accidental section-level header decoration from previous attempts.
# The news sections should retain their normal section headers only.
text = re.sub(r'<style[^>]*>[^<]*THE DAILY[^<]*</style>', '', text, flags=re.I | re.S)

path.write_text(text, encoding="utf-8")
print("Applied newspaper treatment to the page-level header only.")
