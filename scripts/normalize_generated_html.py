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

P.write_text(s, encoding='utf-8')
print('Normalized generated HTML so scripts and styles stay inside the document body.')