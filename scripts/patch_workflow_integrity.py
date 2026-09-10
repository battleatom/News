from pathlib import Path

P = Path('.github/workflows/update-news.yml')
s = P.read_text(encoding='utf-8')


def add_after(anchor, block):
    global s
    if block.strip() in s:
        return
    if anchor not in s:
        raise SystemExit('Workflow anchor not found: ' + anchor.splitlines()[0])
    s = s.replace(anchor, anchor + block, 1)

add_after(
    '      - name: Strengthen event-level duplicate detection\n        run: python scripts/patch_event_dedupe.py\n',
    '\n      - name: Keep exact-link dedupe category scoped\n        run: python scripts/patch_dedupe_scope.py\n',
)
add_after(
    '      - name: Tighten category quality\n        run: python scripts/patch_category_quality.py\n',
    '\n      - name: Canonicalize collector patch artifacts\n        run: python scripts/patch_collector_hygiene.py\n',
)

s = s.replace('      - name: Deduplicate generated UI styles\n', '      - name: Deduplicate generated UI blocks\n', 1)

add_after(
    '      - name: Normalize generated HTML structure\n        run: python scripts/normalize_generated_html.py\n',
    '\n      - name: Audit generated site integrity\n        run: python scripts/site_audit.py\n',
)

cleanup = '''\n      - name: Remove generated Python bytecode\n        run: find scripts -type d -name __pycache__ -prune -exec rm -rf {} +\n'''
anchor = '''          print('Generated page, workflow references, HTML structure, and Python syntax validation passed.')\n          PY\n'''
add_after(anchor, cleanup)

P.write_text(s, encoding='utf-8')
print('Update News Feed workflow now runs collector hygiene, category-scoped dedupe, full site audit, and bytecode cleanup.')
