from pathlib import Path
from collections import Counter, defaultdict
import difflib
import re
import xml.etree.ElementTree as ET

INDEX = Path('index.html')
NEWS = Path('News')

REQUIRED_BLOCK_IDS = (
    'site-features-v2', 'shared-page-state-bridge-v1', 'auto-refresh-timer-v1',
    'alerts-status-v22', 'alerts-new-v23', 'bookmarks-v1', 'nfl-live-v1',
    'load-more-v1', 'top-cycle-reliability-v1', 'legislation-ui-v1',
    'boxoffice-location-v1', 'underreported-ui-v1', 'x-issues-ui-v1', 'region-tab-v1',
)
EXPECTED_TABS = (
    'top','nfl','x','underreported','world','us','presidential','federal','legislation',
    'nm','local','region','technology','gaming','military','boxoffice',
)


def clean(v):
    return re.sub(r'\s+', ' ', v or '').strip()


def title_key(title):
    title = re.sub(r'\s+(?:[-–—|:]\s*)?(?:Reuters|AP News|Associated Press|BBC|CNN|Fox News|NBC News|ABC News|CBS News|NPR|USA Today|IGN(?: Nordic)?|GameSpot|PC Gamer|Polygon)\s*$', '', title, flags=re.I)
    return re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()


def likely_same_title(a, b):
    ka, kb = title_key(a), title_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    wa, wb = set(ka.split()), set(kb.split())
    smaller = min(len(wa), len(wb))
    if smaller >= 5 and len(wa & wb) / smaller >= .86:
        return True
    return min(len(ka), len(kb)) >= 35 and difflib.SequenceMatcher(None, ka, kb).ratio() >= .92


def main():
    errors, warnings = [], []
    html = INDEX.read_text(encoding='utf-8')

    ids = re.findall(r'<(?:script|style)\b[^>]*\bid=["\']([^"\']+)["\']', html, flags=re.I)
    counts = Counter(ids)
    duplicate_ids = {k:v for k,v in counts.items() if v > 1}
    if duplicate_ids:
        errors.append('duplicate generated script/style ids: ' + ', '.join(f'{k}×{v}' for k,v in sorted(duplicate_ids.items())))

    for block_id in REQUIRED_BLOCK_IDS:
        if counts.get(block_id, 0) != 1:
            errors.append(f'{block_id}: expected exactly 1 generated block, found {counts.get(block_id,0)}')

    if counts.get('pull-stats-ui-v1', 0):
        errors.append('legacy pull-stats-ui-v1 controller remains alongside V2.2')
    if counts.get('new-badge-expiry-v1', 0):
        errors.append('retired minute-polling NEW badge controller remains alongside V2.6')
    for marker in ('Next in', 'duplicates removed'):
        if marker not in html:
            errors.append(f'V2.2 status marker missing: {marker}')
    if 'id="sound-alerts-toggle"' in html:
        errors.append('retired alert/sound button is still present')
    if 'infinite-scroll-sentinel' not in html or 'IntersectionObserver' not in html:
        errors.append('infinite-scroll pagination is not wired into generated page')
    for marker in ('__queueNewArticlePopV23', '__markNewArticleLinksV23', '__classifyNewBadgeV26', 'serverFirstSeen', 'stats.firstSeenAt', 'New to Underreported within the last hour'):
        if marker not in html:
            errors.append(f'V2.6 new-article marker missing: {marker}')

    for tab in EXPECTED_TABS:
        if not re.search(rf"\['{re.escape(tab)}'\s*,", html):
            errors.append(f'missing tab declaration: {tab}')

    nfl_wrapper = re.search(
        r"canonicalRender\s*=\s*function\s*\(items\)\s*\{\s*if\s*\(\s*active\s*===\s*['\"]nfl['\"]\s*\)",
        html,
        flags=re.S,
    )
    if 'canonicalBeforeNfl' in html or nfl_wrapper:
        errors.append('retired NFL canonicalRender wrapper is still present')
    if 'function canonicalRender(items)' not in html:
        errors.append('canonicalRender router is missing')
    if 'function renderNfl()' not in html or 'window.renderNfl=renderNfl' not in html:
        errors.append('live NFL renderer is not registered with the canonical router')

    wrapper_count = len(re.findall(r'canonicalRender\s*=\s*function\s*\(items\)', html))
    if wrapper_count:
        warnings.append(f'{wrapper_count} legacy canonicalRender wrapper assignment(s) remain for later consolidation')

    if 'story-search' in html:
        errors.append('retired story search UI is present')

    if html.count('id="auto-refresh-timer-v1"') != 1:
        errors.append('automatic refresh scheduler is not unique')
    if '15*60*1000' not in html and '15 * 60 * 1000' not in html:
        warnings.append('could not confirm 15-minute refresh interval textually')
    if 'STORIES_PER_PAGE = 10' not in html:
        errors.append('10-story pagination constant is missing')

    tree = ET.parse(NEWS)
    items = tree.getroot().findall('./channel/item')
    by_category = defaultdict(list)
    same_cat_links = defaultdict(list)
    official_legislation = 0
    for item in items:
        cat = clean(item.findtext('category')) or 'world'
        title = clean(item.findtext('title'))
        link = clean(item.findtext('link'))
        by_category[cat].append((title, link))
        if link:
            same_cat_links[(cat, link)].append(title)
        if cat == 'legislation' and clean(item.findtext('officialSource')):
            official_legislation += 1

    exact_dups = [(cat, link, titles) for (cat,link),titles in same_cat_links.items() if len(titles) > 1]
    if exact_dups:
        errors.append(f'{len(exact_dups)} exact-link duplicate(s) remain inside a category')

    semantic = []
    for cat, rows in by_category.items():
        for i in range(len(rows)):
            for j in range(i+1, len(rows)):
                if likely_same_title(rows[i][0], rows[j][0]):
                    semantic.append((cat, rows[i][0], rows[j][0]))
                    if len(semantic) >= 20:
                        break
            if len(semantic) >= 20:
                break
        if len(semantic) >= 20:
            break
    if semantic:
        warnings.append(f'{len(semantic)} likely same-story title pair(s) remain after dedupe; review thresholds')

    legislation_count = len(by_category.get('legislation', []))
    if legislation_count < 11:
        errors.append(f'legislation pool has only {legislation_count} records; infinite scroll cannot paginate')
    if official_legislation < min(10, legislation_count):
        errors.append(f'only {official_legislation}/{legislation_count} legislation records have official sources')

    pool_order = ['top','nfl','x','underreported','world','us','presidential','federal','legislation','nm','local','region','technology','gaming','military']
    print('SITE AUDIT — FEED POOLS')
    for cat in pool_order:
        print(f'  {cat:14} {len(by_category.get(cat, [])):3}')
    print(f'  total          {len(items):3}')
    print(f'  official legis {official_legislation:3}')
    print(f'  generated ids  {len(counts):3} unique')
    print(f'  likely dupes   {len(semantic):3} pairs')
    for cat,a,b in semantic[:8]:
        print(f'    WARN duplicate? [{cat}] {a} || {b}')
    for w in warnings:
        print('WARNING:', w)
    if errors:
        for e in errors:
            print('ERROR:', e)
        raise SystemExit(f'Site audit failed with {len(errors)} error(s).')
    print('Site audit passed: canonical routing, V2.2 status, V2.6 NEW timing, tabs, infinite scroll, official legislation, and exact within-category dedupe verified.')


if __name__ == '__main__':
    main()
