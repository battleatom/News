from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

for style_id in ('site-features-style', 'nfl-live-style'):
    pattern = re.compile(rf'<style\s+id=["\']{re.escape(style_id)}["\']>.*?</style>\s*', re.I | re.S)
    matches = list(pattern.finditer(s))
    if len(matches) > 1:
        for m in reversed(matches[1:]):
            s = s[:m.start()] + s[m.end():]
        print(f'Removed {len(matches) - 1} duplicate {style_id} style block(s).')

p.write_text(s, encoding='utf-8')
print('Generated UI style deduplication complete.')
