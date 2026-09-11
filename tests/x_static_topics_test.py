#!/usr/bin/env python3
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('xissues',ROOT/'scripts/enrich_x_issues.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
expected=['Health','Technology & AI','Celebrities & Public Figures','World','Politics & Government','Entertainment','Sports','Business & Economy','Gaming','Science']
assert mod.EXPECTED_TOPICS==expected
assert len(mod.CATEGORIES)==10
assert len(set(mod.EXPECTED_TOPICS))==10
workflow=(ROOT/'.github/workflows/update-news.yml').read_text(encoding='utf-8')
assert 'Rebuild fixed X Top Issues from verified feed' in workflow
assert 'Verify exactly ten fixed X topics' in workflow
ui=(ROOT/'scripts/patch_x_ui.py').read_text(encoding='utf-8')
assert "==='x'" in ui
print('X static topic contract test passed.')
