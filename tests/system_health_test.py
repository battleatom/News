import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,'scripts/system_health.py','--stage','test'],cwd=ROOT,check=True)
data=json.loads((ROOT/'refresh-health.json').read_text(encoding='utf-8'))
assert data['status']=='healthy',data
assert data['code'] is None
assert len(data['systems'])==4
assert all(x['status']=='healthy' for x in data['systems'])
subprocess.run([sys.executable,'scripts/build_site.py'],cwd=ROOT,check=True)
html=(ROOT/'index.html').read_text(encoding='utf-8')
assert 'id="system-health-v1"' in html
assert 'id="system-health-v1-style"' in html
assert 'System Health' in html
assert 'sh-dot' in html
assert 'aria-expanded' in html
print('System Health diagnostics and generated UI regression passed.')
