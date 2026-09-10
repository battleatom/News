from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')

# Canonical imports used by the bounded local-query worker pool.
if 'from concurrent.futures import ThreadPoolExecutor, as_completed' not in s:
    s=s.replace('import xml.etree.ElementTree as ET\n','import xml.etree.ElementTree as ET\nfrom concurrent.futures import ThreadPoolExecutor, as_completed\n',1)

# Older idempotent patchers occasionally appended the same literal more than once.
weight_match = re.search(r'CATEGORY_WEIGHT\s*=\s*\{.*?\}\n', s, flags=re.S)
if weight_match:
    canonical = 'CATEGORY_WEIGHT = {"world": 18, "us": 22, "presidential": 24, "federal": 22, "legislation": 24, "military": 20, "nfl": 18, "technology": 12, "gaming": 16, "nm": 8, "local": 6}\n'
    s = s[:weight_match.start()] + canonical + s[weight_match.end():]
s = re.sub(r'("route fifty",\s*){2,}', '"route fifty", ', s)

POOL_MINIMUMS = {
    "local": 20,
    "nfl": 20,
    "presidential": 20,
    "federal": 25,
    "technology": 25,
    "gaming": 25,
}
minimum_block = 'CATEGORY_POOL_MINIMUMS = ' + repr(POOL_MINIMUMS) + '\n'
if 'CATEGORY_POOL_MINIMUMS =' in s:
    s = re.sub(r'CATEGORY_POOL_MINIMUMS\s*=\s*\{.*?\}\n', minimum_block, s, count=1, flags=re.S)
else:
    pos=s.find('CATEGORY_WEIGHT = ')
    if pos<0:raise SystemExit('Could not locate category weights for pool minimums')
    line_end=s.find('\n',pos)
    s=s[:line_end+1]+minimum_block+s[line_end+1:]

presidential_queries = '''    "presidential": [
        "Trump president White House",
        "President Trump administration White House policy",
        "Trump executive order presidential action White House",
        "Trump cabinet administration president",
    ],
'''
s, changed = re.subn(r'    "presidential":\s*(?:"[^"]*"|\[.*?\]),\n    "federal":', presidential_queries + '    "federal":', s, count=1, flags=re.S)
if changed != 1:raise SystemExit("Could not canonicalize QUERIES['presidential']")

fallback_entries = '''    "presidential": [
        ("Reuters", "site:reuters.com Trump White House president administration"),
        ("Associated Press", "site:apnews.com Trump White House president administration"),
        ("Politico", "site:politico.com Trump White House president administration"),
        ("CNN", "site:cnn.com Trump White House president administration"),
        ("CBS News", "site:cbsnews.com Trump White House president administration"),
    ],
    "federal": [
        ("Reuters", "site:reuters.com Congress Supreme Court DOJ FBI federal agency government"),
        ("Associated Press", "site:apnews.com Congress Supreme Court DOJ FBI federal government"),
        ("Politico", "site:politico.com Congress Supreme Court federal agency government"),
        ("The Hill", "site:thehill.com Congress Supreme Court federal agency government"),
        ("NPR", "site:npr.org Congress Supreme Court federal government agency"),
    ],
'''
fallback_anchor='TRUSTED_CATEGORY_FALLBACKS = {\n'
fallback_start=s.find(fallback_anchor)
if fallback_start<0:raise SystemExit('Could not locate trusted category fallbacks')
fallback_body_start=fallback_start+len(fallback_anchor)
fallback_end=s.find('\n}',fallback_body_start)
if fallback_end<0:raise SystemExit('Could not locate end of trusted category fallbacks')
fallback_body=s[fallback_body_start:fallback_end]
for key in ('presidential','federal'):
    fallback_body=re.sub(rf'    "{key}": \[\n(?:        .*\n)*?    \],\n','',fallback_body,count=1)
s=s[:fallback_body_start]+fallback_entries+fallback_body+s[fallback_end:]

s=s.replace('if category in TRUSTED_CATEGORY_FALLBACKS and usable_count < 10:','if category in TRUSTED_CATEGORY_FALLBACKS and usable_count < CATEGORY_POOL_MINIMUMS.get(category, 10):')
s=s.replace('target = 15 if category == "local" else 20','target = CATEGORY_POOL_MINIMUMS.get(category, 20)')
old='''                            target = CATEGORY_POOL_MINIMUMS.get(category, 20)\n                            if usable_count >= target:\n                                break'''
new='''                            target = CATEGORY_POOL_MINIMUMS.get(category, 20)\n                            if usable_count >= target and category not in ("gaming", "technology"):\n                                break'''
if old in s:s=s.replace(old,new,1)
elif 'category not in ("gaming", "technology")' not in s:raise SystemExit('Could not install diversified Gaming/Technology fallback collection')

# Cache raw RSS responses for the duration of one collector run. Region and
# fallback queries overlap substantially, so this prevents duplicate requests.
old_fetch='''def fetch(query):
    req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 NewsBrief/1.4"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read())
'''
new_fetch='''FETCH_CACHE = {}


def fetch(query):
    cache_key = str(query).strip()
    payload = FETCH_CACHE.get(cache_key)
    if payload is None:
        req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 NewsBrief/2.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = response.read()
        FETCH_CACHE[cache_key] = payload
    return ET.fromstring(payload)
'''
if old_fetch in s:s=s.replace(old_fetch,new_fetch,1)
elif 'FETCH_CACHE = {}' not in s:raise SystemExit('Could not install per-run RSS request cache')

# Replace the accidentally repeated Local fallback blocks with one canonical,
# bounded-concurrency collection path. This is deliberately limited to six
# workers so the refresh is faster without hammering Google News.
local_start=s.find('            if category == "local":\n')
region_start=s.find('            elif category == "region":\n',local_start)
if local_start<0 or region_start<0:raise SystemExit('Could not locate Local collector branch')
local_block='''            if category == "local":
                items = []
                worker_count = max(1, min(6, len(LOCAL_QUERIES)))
                with ThreadPoolExecutor(max_workers=worker_count) as pool:
                    jobs = {pool.submit(fetch, local_query): local_query for local_query in LOCAL_QUERIES}
                    for job in as_completed(jobs):
                        local_query = jobs[job]
                        try:
                            batch = parse_items(job.result(), category)
                            print(f"local/{local_query}: {len(batch)} fresh stories")
                            items.extend(batch)
                        except Exception as exc:
                            print(f"Local feed failed for {local_query}: {exc}")
                usable_count = len(select_category_stories(items, limit=30))
                target = CATEGORY_POOL_MINIMUMS.get("local", 20)
                if usable_count < target:
                    for fallback_source, fallback_query in TRUSTED_CATEGORY_FALLBACKS.get("local", []):
                        try:
                            batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                            items.extend(batch)
                            usable_count = len(select_category_stories(items, limit=30))
                            print(f"local fallback/{fallback_source}: {len(batch)} accepted; {usable_count} usable local stories")
                            if usable_count >= target:
                                break
                        except Exception as exc:
                            print(f"Local fallback failed for {fallback_source}: {exc}")
'''
s=s[:local_start]+local_block+s[region_start:]

P.write_text(s,encoding='utf-8')
print('Collector hygiene complete: duplicate Local fallbacks removed, RSS cached per run, and Local queries use bounded concurrency.')
