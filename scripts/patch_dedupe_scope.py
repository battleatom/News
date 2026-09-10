from pathlib import Path

P = Path('scripts/dedupe_news_stories.py')
s = P.read_text(encoding='utf-8')

old = '''        link = clean(item.findtext("link")).strip()\n        if link and link in seen_links:\n            removed_exact += 1\n            continue\n        if any(same_story(item, prior) for prior in kept):\n            removed_similar += 1\n            continue\n        if link:\n            seen_links.add(link)\n        kept.append(item)'''
new = '''        link = clean(item.findtext("link")).strip()\n        category = clean(item.findtext("category")).strip()\n        link_key = (category, link)\n        if link and link_key in seen_links:\n            removed_exact += 1\n            continue\n        if any(same_story(item, prior) for prior in kept):\n            removed_similar += 1\n            continue\n        if link:\n            seen_links.add(link_key)\n        kept.append(item)'''

if old in s:
    s = s.replace(old, new, 1)
elif 'link_key = (category, link)' not in s:
    raise SystemExit('Could not patch category-scoped exact-link dedupe')

P.write_text(s, encoding='utf-8')
print('Exact-link dedupe is category-scoped; valid cross-tab copies are preserved.')
