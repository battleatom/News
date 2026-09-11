from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')

# Fetch a wider three-day candidate window. Final selectors remain newest-first,
# so older stories only backfill categories that cannot fill from fresher items.
s = s.replace('MAX_AGE_HOURS = 48', 'MAX_AGE_HOURS = 72')
s = s.replace('f"{query} when:2d"', 'f"{query} when:3d"')

# One consistent pool policy for ordinary news tabs. Underreported and X have
# their own editorial models; Local remains intentionally smaller because its
# geographic source pool is naturally narrower.
minimums = {
    'world': 30,
    'us': 30,
    'presidential': 30,
    'federal': 30,
    'legislation': 30,
    'nm': 25,
    'local': 20,
    'region': 30,
    'nfl': 30,
    'technology': 30,
    'gaming': 30,
    'military': 30,
}
s = re.sub(
    r'CATEGORY_POOL_MINIMUMS\s*=\s*\{.*?\}\n',
    'CATEGORY_POOL_MINIMUMS = ' + repr(minimums) + '\n',
    s,
    count=1,
    flags=re.S,
)

# Trusted backfill queries for categories that previously had no minimum-pool
# recovery path. These are only used when the deduped usable pool is under its
# minimum target.
marker = 'CATEGORY_WEIGHT = '
if 'CATEGORY_POOL_FALLBACKS_V2 = True' not in s:
    extra = '''\n# Normalized pool backfills for categories that historically underfilled.\nCATEGORY_POOL_FALLBACKS_V2 = True\nTRUSTED_CATEGORY_FALLBACKS.update({\n    "world": [\n        ("Reuters", "site:reuters.com world international breaking news"),\n        ("Associated Press", "site:apnews.com world international breaking news"),\n        ("BBC", "site:bbc.com/news world international"),\n        ("Al Jazeera", "site:aljazeera.com world international"),\n    ],\n    "us": [\n        ("Reuters", "site:reuters.com United States US politics national news"),\n        ("Associated Press", "site:apnews.com United States US politics national news"),\n        ("NPR", "site:npr.org United States national politics news"),\n        ("CBS News", "site:cbsnews.com US national politics news"),\n    ],\n    "nm": [\n        ("Albuquerque Journal", "site:abqjournal.com New Mexico news"),\n        ("Source New Mexico", "site:sourcenm.com New Mexico government politics news"),\n        ("KRQE", "site:krqe.com New Mexico news"),\n        ("KOAT", "site:koat.com New Mexico news"),\n        ("KOB 4", "site:kob.com New Mexico news"),\n    ],\n    "military": [\n        ("Defense News", "site:defensenews.com military Pentagon defense"),\n        ("Breaking Defense", "site:breakingdefense.com military Pentagon defense"),\n        ("Reuters", "site:reuters.com US military Pentagon defense"),\n        ("Associated Press", "site:apnews.com US military Pentagon defense"),\n    ],\n})\n\n'''
    if marker not in s:
        raise SystemExit('Could not locate category-weight marker for fallback insertion')
    s = s.replace(marker, extra + marker, 1)

# Select a balanced 35-story ordinary pool. Forty remains the hard ceiling used
# by Region, while Local is capped separately by its narrower policy.
s = s.replace('def select_category_stories(items, limit=30):', 'def select_category_stories(items, limit=35):')
s = s.replace('"""Select up to 30 distinct stories, with Local queries treated as the geographic scope."""',
              '"""Select a balanced newest-first category pool, normally capped at 35 stories."""')

# Fallback decisions must use the post-dedupe usable count, not raw query count.
old = '''                own_count = sum(1 for item in items if item.get("category") == category)\n                usable_count = len(select_category_stories(items, limit=30)) if category == "local" else own_count'''
new = '''                own_count = sum(1 for item in items if item.get("category") == category)\n                pool_limit = 30 if category == "local" else 35\n                usable_count = len(select_category_stories(items, limit=pool_limit))'''
if old in s:
    s = s.replace(old, new, 1)
elif 'pool_limit = 30 if category == "local" else 35' not in s:
    raise SystemExit('Could not normalize initial usable-count calculation')

old = '''                            own_count = sum(1 for item in items if item.get("category") == category)\n                            usable_count = len(select_category_stories(items, limit=30)) if category == "local" else own_count'''
new = '''                            own_count = sum(1 for item in items if item.get("category") == category)\n                            pool_limit = 30 if category == "local" else 35\n                            usable_count = len(select_category_stories(items, limit=pool_limit))'''
if old in s:
    s = s.replace(old, new, 1)
elif s.count('pool_limit = 30 if category == "local" else 35') < 2:
    raise SystemExit('Could not normalize fallback usable-count calculation')

# Once the minimum is satisfied, stop fallback expansion for every category.
s = s.replace('if usable_count >= target and category not in ("gaming", "technology"):',
              'if usable_count >= target:')

# Region previously built up to 80 stories *per subregion* and then concatenated
# them. Use one nationally balanced regional pool with a hard 40-story ceiling.
old_region = '''        if category == "region":\n            selected_by_category[category] = []\n            for region_name in ("southwest", "west", "mountain", "midwest", "south", "northeast", "pacific-northwest", "southeast"):\n                region_items = [x for x in category_items if x.get("region") == region_name]\n                selected_by_category[category].extend(select_region_stories(region_items, per_state=8, limit=80))\n        else:\n            selected_by_category[category] = select_category_stories(category_items)'''
new_region = '''        if category == "region":\n            selected_by_category[category] = select_region_stories(category_items, per_state=4, limit=40)\n        elif category == "local":\n            selected_by_category[category] = select_category_stories(category_items, limit=30)\n        else:\n            selected_by_category[category] = select_category_stories(category_items, limit=35)'''
if old_region in s:
    s = s.replace(old_region, new_region, 1)
elif 'select_region_stories(category_items, per_state=4, limit=40)' not in s:
    raise SystemExit('Could not normalize Region final pool')

P.write_text(s, encoding='utf-8')
print('Normalized category pools: 72h candidate window, deduped minimum checks, 35-story standard pools, 40-story Region ceiling.')
