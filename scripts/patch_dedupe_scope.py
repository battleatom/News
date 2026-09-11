from pathlib import Path

CANDIDATES = (
    Path('scripts/dedupe_news_legacy.py'),
    Path('scripts/dedupe_news_stories.py'),
)

old = '''        link = clean(item.findtext("link")).strip()\n        if link and link in seen_links:\n            removed_exact += 1\n            continue\n        if any(same_story(item, prior) for prior in kept):\n            removed_similar += 1\n            continue\n        if link:\n            seen_links.add(link)\n        kept.append(item)'''
new = '''        link = clean(item.findtext("link")).strip()\n        category = clean(item.findtext("category")).strip()\n        link_key = (category, link)\n        if link and link_key in seen_links:\n            removed_exact += 1\n            continue\n        if any(same_story(item, prior) for prior in kept):\n            removed_similar += 1\n            continue\n        if link:\n            seen_links.add(link_key)\n        kept.append(item)'''

verified = False
for path in CANDIDATES:
    if not path.exists():
        continue
    s = path.read_text(encoding='utf-8')
    if 'link_key = (category, link)' in s:
        verified = True
        continue
    if old in s:
        path.write_text(s.replace(old, new, 1), encoding='utf-8')
        verified = True

if not verified:
    raise SystemExit('Could not verify category-scoped exact-link dedupe')

print('Exact-link dedupe is category-scoped; legacy and wrapped dedupe layouts are supported.')
