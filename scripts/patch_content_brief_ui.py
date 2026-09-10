from pathlib import Path
import re

P = Path("index.html")
s = P.read_text(encoding="utf-8")

# Idempotently keep exactly one content-brief stylesheet link.
s = re.sub(r'\s*<link\s+rel=["\']stylesheet["\']\s+href=["\']styles/content-briefs\.css(?:\?[^"\']*)?["\']\s*/?>', '', s, flags=re.I)
link = '<link rel="stylesheet" href="styles/content-briefs.css?v=1">'
if '</head>' not in s:
    raise SystemExit('Generated page is missing </head>')
s = s.replace('</head>', link + '\n</head>', 1)

# Marker used by preview validation and future maintenance.
s = re.sub(r'\sdata-content-briefs=["\'][^"\']*["\']', '', s, count=1)
s = s.replace('<html', '<html data-content-briefs="1"', 1)

P.write_text(s, encoding="utf-8")
print('Enabled V3 content brief presentation.')
