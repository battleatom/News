from pathlib import Path
import re

p = Path('scripts/enrich_x_issues.py')
s = p.read_text(encoding='utf-8')

new = r'''def trend_candidates(category, query):
    # Do not require a trend name to literally contain category words.
    names = fetch_trend_names()
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    candidates = []

    for name in names[:60]:
        try:
            rss = fetch(f'"{name}"')
        except Exception:
            continue
        for item in rss.findall('.//item'):
            d = news_item_data(item)
            if not d['dt'] or not d['title'] or len(d['desc']) < 70:
                continue
            link = d['link'].lower()
            if 'x.com/' in link or 'twitter.com/' in link:
                continue
            title_words = words(d['title'] + ' ' + d['desc'])
            trend_words = words(name)
            overlap = len(title_words & trend_words)
            category_hits = len(title_words & terms)
            if not overlap:
                continue
            if category_hits == 0 and overlap < 2:
                continue
            candidates.append((category_hits, overlap, d, name))

    candidates.sort(key=lambda x: (x[0], x[1], x[2]['dt']), reverse=True)
    return candidates
'''

pattern = r"def trend_candidates\(category, query\):[\s\S]*?\n\ndef broad_candidates\(query\):"
s2, n = re.subn(pattern, new + "\n\ndef broad_candidates(query):", s, count=1)
if n != 1:
    raise SystemExit('Could not patch trend_candidates')

s2 = s2.replace(', "zelda"', '')
# The category-coverage patch returns four fields; make downstream code accept both
# the original 3-field candidates and the enriched 4-field candidates.
s2 = s2.replace('overlap,d,name=row', 'overlap,d,name,*extra=row')
s2 = s2.replace('_,lead,trend=best', '_,lead,trend,*extra=best')
p.write_text(s2, encoding='utf-8')
print('Patched X category coverage and candidate tuple compatibility.')
