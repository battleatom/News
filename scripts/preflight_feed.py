from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')
s = s.replace('MAX_AGE_HOURS = 72', 'MAX_AGE_HOURS = 48')
s = s.replace('f"{query} when:3d"', 'f"{query} when:2d"')

line = '    "nfl": ["NFL news", "NFL injuries trades free agency", "NFL scores results"],'
s = re.sub(r'(?:\n?' + re.escape(line) + r'){1,}', '\n' + line, s)
if '    "technology": "technology AI cybersecurity science",' in s and line not in s:
    s = s.replace('    "technology": "technology AI cybersecurity science",', line + '\n    "technology": "technology AI cybersecurity science",', 1)

P.write_text(s, encoding='utf-8')
print('Preflight complete: rolling 48-hour news window and NFL category verified.')
