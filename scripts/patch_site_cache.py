from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")
needle = '<meta charset="UTF-8">'
meta = '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">'
if meta not in text and needle in text:
    text = text.replace(needle, needle + meta, 1)
path.write_text(text, encoding="utf-8")
