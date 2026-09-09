from pathlib import Path
import re

P = Path('index.html')
s = P.read_text(encoding='utf-8')

if '</body>' not in s or '</html>' not in s:
    raise SystemExit('Generated page is missing </body> or </html>')

body_end = s.rfind('</body>')
html_end = s.rfind('</html>')
if html_end < body_end:
    raise SystemExit('Malformed page: </html> appears before </body>')

tail = s[html_end + len('</html>'):]
tags = re.findall(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', tail, flags=re.I | re.S)
remainder = re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', '', tail, flags=re.I | re.S).strip()
if remainder:
    raise SystemExit('Unexpected content exists after </html>: ' + remainder[:120])

if tags or tail.strip():
    body_prefix = s[:body_end]
    s = body_prefix + ('\n' + '\n'.join(tags) if tags else '') + '\n</body>\n</html>\n'

# Hard guarantees: there must be one automatic scheduler and no legacy/competing
# refresh loops. The timer patch owns scheduling; site-features owns rendering/status.
if s.count('id="auto-refresh-timer-v1"') != 1:
    raise SystemExit('Expected exactly one auto refresh timer script')
if re.search(r'setInterval\(\(\)\s*=>\s*loadNews\(false\)', s):
    raise SystemExit('Legacy 15-minute loadNews scheduler still exists')
if re.search(r'setInterval\(\(\)\s*=>\s*\{\s*if\(lastSuccessfulPull\s*&&\s*Date\.now\(\)\s*>=\s*nextScheduledPull\s*&&\s*!pullInProgress\)', s):
    raise SystemExit('Competing five-second refresh scheduler still exists')

P.write_text(s, encoding='utf-8')
print('Normalized generated HTML and verified there is only one automatic refresh scheduler.')