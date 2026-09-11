from __future__ import annotations

import argparse
import json
import py_compile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'refresh-health.json'
REQUIRED = ['News', 'index.html', 'update-stats.json']


def check(name, code, fn):
    try:
        detail = fn()
        return {'name': name, 'status': 'healthy', 'code': None, 'message': detail or 'Operational'}
    except Exception as exc:
        return {'name': name, 'status': 'critical', 'code': code, 'message': str(exc)[:240]}


def required_files():
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing: raise RuntimeError('Missing required file(s): ' + ', '.join(missing))
    return 'Required files present'


def python_syntax():
    for p in (ROOT / 'scripts').glob('*.py'):
        py_compile.compile(str(p), doraise=True)
    return 'Python syntax valid'


def feed_valid():
    root = ET.parse(ROOT / 'News').getroot()
    count = len(root.findall('./channel/item'))
    if count < 1: raise RuntimeError('Feed contains no stories')
    return f'{count} feed stories parsed'


def stats_valid():
    data = json.loads((ROOT / 'update-stats.json').read_text(encoding='utf-8'))
    if not data.get('updatedAt'): raise RuntimeError('update-stats.json has no updatedAt')
    return 'Update statistics readable'


def build_health(stage='preflight'):
    systems = [
        check('Required files', 'PRE-001', required_files),
        check('Python', 'PRE-002', python_syntax),
        check('Feed', 'SRC-102', feed_valid),
        check('Update statistics', 'PRE-003', stats_valid),
    ]
    worst = 'healthy' if all(x['status'] == 'healthy' for x in systems) else 'critical'
    first = next((x for x in systems if x['status'] != 'healthy'), None)
    payload = {
        'status': worst,
        'stage': stage,
        'code': first['code'] if first else None,
        'message': first['message'] if first else 'All preflight checks passed.',
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'systems': systems,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='preflight')
    ap.add_argument('--no-fail', action='store_true')
    args = ap.parse_args()
    data = build_health(args.stage)
    print(f"System Health: {data['status']} {data.get('code') or 'OK'} — {data['message']}")
    if data['status'] == 'critical' and not args.no_fail:
        raise SystemExit(1)


if __name__ == '__main__': main()
