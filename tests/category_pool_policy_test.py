from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, 'scripts/patch_category_pool_policy.py'], cwd=ROOT, check=True)

spec = importlib.util.spec_from_file_location('update_news_policy_test', ROOT / 'scripts' / 'update_news.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert mod.MAX_AGE_HOURS == 72
assert 'when:3d' in mod.feed_url('test query')

expected_minimums = {
    'world': 30, 'us': 30, 'presidential': 30, 'federal': 30,
    'legislation': 30, 'nm': 25, 'local': 20, 'region': 30,
    'nfl': 30, 'technology': 30, 'gaming': 30, 'military': 30,
}
assert mod.CATEGORY_POOL_MINIMUMS == expected_minimums
for name in ('world', 'us', 'nm', 'military'):
    assert name in mod.TRUSTED_CATEGORY_FALLBACKS
    assert len(mod.TRUSTED_CATEGORY_FALLBACKS[name]) >= 4

now = datetime.now(timezone.utc)

def item(i, category='us', state=''):
    return {
        'title': f'Unique policy test story {category} {state} {i}',
        'description': f'Distinct reporting item number {i}',
        'link': f'https://example.com/{category}/{state}/{i}',
        'source': f'Test Source {i % 12}',
        'category': category,
        'state': state,
        'region': 'test-region',
        'published': now - timedelta(minutes=i),
        'pubDate': 'Fri, 11 Sep 2026 12:00:00 GMT',
    }

ordinary = [item(i) for i in range(55)]
selected = mod.select_category_stories(ordinary)
assert len(selected) == 35, len(selected)
assert selected[0]['published'] >= selected[-1]['published']

states = ['Arizona','Colorado','Utah','Nevada','Idaho','Montana','Wyoming','Texas','Ohio','Michigan','Florida','Georgia']
regional = []
for sidx, state in enumerate(states):
    for j in range(6):
        regional.append(item(sidx * 10 + j, category='region', state=state))
region_selected = mod.select_region_stories(regional, per_state=4, limit=40)
assert len(region_selected) == 40, len(region_selected)
assert len({x['state'] for x in region_selected}) >= 10

source = (ROOT / 'scripts' / 'update_news.py').read_text(encoding='utf-8')
assert 'select_region_stories(category_items, per_state=4, limit=40)' in source
assert 'selected_by_category[category].extend(select_region_stories(region_items, per_state=8, limit=80))' not in source
assert source.count('pool_limit = 30 if category == "local" else 35') >= 2

print('Category pool policy regression passed: 72h candidate backfill, 35-story standard pools, 40-story Region ceiling.')
