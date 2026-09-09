from pathlib import Path
import re

path = Path("scripts/update_news.py")
text = path.read_text(encoding="utf-8")

# Only admit publishers with an established editorial/news operation. Google News
# is the aggregator, not the trust decision: the publisher itself must be approved.
TRUSTED_SOURCE_ALIASES = [
    "reuters", "associated press", "ap", "bbc", "npr", "pbs", "afp", "france 24", "france24",
    "deutsche welle", "dw", "the guardian", "sky news", "al jazeera", "euronews", "cbc", "nhk",
    "abc australia", "australian broadcasting corporation", "aap", "swissinfo", "rfi",
    "cnn", "nbc news", "abc news", "cbs news", "fox news", "usa today", "new york times",
    "washington post", "wall street journal", "wsj", "los angeles times", "chicago tribune",
    "boston globe", "politico", "axios", "the hill", "newsweek", "time", "usatoday",
    "bloomberg", "cnbc", "forbes", "yahoo news", "yahoo finance", "associated press",
    "farmington daily times", "daily times", "albuquerque journal", "santa fe new mexican",
    "las cruces sun-news", "krqe", "koat", "kob 4", "kob tv", "kfox", "kvia", "nm political report",
    "new mexico in depth", "durango herald", "durango telegraph", "the colorado sun", "denver post",
    "azcentral", "arizona republic", "colorado public radio", "krdo", "koaa", "denver7",
    "the verge", "ars technica", "techcrunch", "wired", "engadget", "tom's hardware", "pcmag",
    "pc magazine", "mit technology review", "scientific american", "nature", "space.com",
    "ign", "gamespot", "polygon", "eurogamer", "pc gamer", "game informer", "kotaku",
    "nintendo life", "destructoid", "rock paper shotgun", "the gamer",
    "defense news", "military times", "stars and stripes", "breaking defense", "janes", "war on the rocks",
    "times of india", "the hindu", "south china morning post", "kyiv independent", "jerusalem post",
    "haaretz", "times of israel", "the times", "the telegraph", "politico europe", "der spiegel",
    "le monde", "el pais", "corriere della sera", "deutsche presse-agentur", "dpa",
]
TRUSTED_SOURCE_TOKENS = tuple(sorted({re.sub(r"[^a-z0-9]+", " ", x.lower()).strip() for x in TRUSTED_SOURCE_ALIASES if x}))

def source_is_trusted(source):
    s = re.sub(r"[^a-z0-9]+", " ", (source or "").lower()).strip()
    if not s:
        return False
    return any(s == token or token in s for token in TRUSTED_SOURCE_TOKENS)

FOREIGN_ONLY_TERMS = (
    "germany", "german", "berlin", "france", "french", "paris", "united kingdom", "britain",
    "british", "london", "italy", "italian", "rome", "spain", "spanish", "madrid", "europe",
    "european union", "eu", "ukraine", "ukrainian", "russia", "russian", "moscow", "china", "chinese",
    "beijing", "japan", "japanese", "tokyo", "south korea", "korean", "india", "indian", "africa",
    "african", "south africa", "nigeria", "kenya", "ethiopia", "ghana", "egypt", "cairo", "israel",
    "israeli", "gaza", "palestine", "iran", "iranian", "tehran", "iraq", "iraqi", "syria", "syrian",
    "lebanon", "turkey", "turkish", "australia", "australian", "canada", "canadian", "mexico", "mexican",
    "brazil", "brazilian", "argentina", "argentine", "colombia", "philippines", "indonesia", "taiwan",
    "new zealand", "pakistan", "afghanistan", "north korea", "nato", "united nations", "west bank",
)
US_CONTEXT_TERMS = (
    "united states", "u.s.", "us ", "america", "american", "washington dc", "washington, d.c.",
    "new mexico", "farmington", "san juan county", "arizona", "colorado", "utah", "nevada", "texas",
    "california", "oregon", "washington state", "new york", "florida", "georgia", "illinois", "ohio",
    "congress", "senate", "house of representatives", "white house", "pentagon", "supreme court",
)

def should_route_to_world(title, description, category):
    if category == "world":
        return False
    text = f"{title} {description}".lower()
    foreign_hits = sum(1 for term in FOREIGN_ONLY_TERMS if term in text)
    us_hits = sum(1 for term in US_CONTEXT_TERMS if term in text)
    return foreign_hits >= 2 and us_hits == 0

# Keep the existing Four Corners Local tab exactly as its own fixed geographic feed.
old_local = '    "local": "Farmington New Mexico OR San Juan County New Mexico OR Aztec New Mexico OR Bloomfield New Mexico OR Kirtland New Mexico OR Shiprock New Mexico OR Four Corners New Mexico",'
new_local = '''    "local": [
        "Farmington New Mexico news",
        "San Juan County New Mexico news",
        "Aztec New Mexico news",
        "Bloomfield New Mexico news",
        "Kirtland New Mexico news",
        "Shiprock New Mexico news",
        "Four Corners New Mexico news",
        "Farmington NM crime OR government OR education OR business",
    ],'''
if old_local in text:
    text = text.replace(old_local, new_local)

old_local_block = '''    "local": [
        "Farmington New Mexico",
        "San Juan County New Mexico",
        "Aztec New Mexico",
        "Bloomfield New Mexico",
        "Kirtland New Mexico",
        "Shiprock New Mexico",
        "Four Corners New Mexico",
    ],'''
if old_local_block in text:
    text = text.replace(old_local_block, new_local)

# NFL is a dedicated tab with its own news pool; live scores are rendered client-side.
if '    "nfl": [' not in text:
    anchor = '    "world": '
    idx = text.find(anchor)
    if idx != -1:
        text = text[:idx] + '''    "nfl": [
        "NFL news",
        "NFL injuries trades free agency",
        "NFL scores results",
    ],
''' + text[idx:]

text = re.sub(r'^\s*"nfl":\s*"NFL football news OR NFL scores OR NFL injuries OR NFL trades OR NFL teams",\s*\n', '', text, flags=re.M)
text = re.sub(r'    "x": \[\n(?:.*\n)*?    \],\n', '', text, count=1)

match = re.search(r'SECTIONS\s*=\s*\[[^\n]+\]', text)
if match:
    sections = match.group(0)
    sections = sections.replace('"x", ', '').replace(', "x"', '')
    text = text[:match.start()] + sections + text[match.end():]

# Reject unapproved publishers and move clear foreign-only stories into World.
source_anchor = '        source = source_override or clean(source_el.text if source_el is not None else "")\n'
source_guard = '''        source = source_override or clean(source_el.text if source_el is not None else "")
        if not source_is_trusted(source):
            continue
        if should_route_to_world(title, desc, category):
            category = "world"
'''
if source_anchor in text and 'if not source_is_trusted(source):' not in text:
    text = text.replace(source_anchor, source_guard, 1)

old_loop = '''    for category, query in QUERIES.items():
        try:
            items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories")
            all_items.extend(items)
        except Exception as exc:
            print(f"Feed failed for {category}: {exc}")'''
new_loop = '''    for category, query in QUERIES.items():
        if category == "region":
            items = []
            for region_name, region_queries in query.items():
                for region_query in region_queries:
                    try:
                        batch = parse_items(fetch(region_query), category)
                        for item in batch:
                            item["region"] = region_name
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Region feed failed for {region_name}/{region_query}: {exc}")
            print(f"region: {len(items)} fresh stories")
        else:
            queries = query if isinstance(query, list) else [query]
            items = []
            for q in queries:
                try:
                    items.extend(parse_items(fetch(q), category))
                except Exception as exc:
                    print(f"Feed failed for {category}/{q}: {exc}")
            print(f"{category}: {len(items)} fresh stories")
        all_items.extend(items)'''
if old_loop in text:
    text = text.replace(old_loop, new_loop)

old_region_loop = '''            elif category == "region":
                items = []
                region_names = [
                    "southwest", "west", "mountain", "midwest",
                    "south", "northeast", "pacific-northwest", "southeast",
                ]
                for region_name, region_query in zip(region_names, query):
                    try:
                        batch = parse_items(fetch(region_query), category)
                        for item in batch:
                            item["region"] = region_name
                        print(f"region/{region_name}: {len(batch)} fresh stories")
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Region feed failed for {region_name}: {exc}")'''
new_region_loop = '''            elif category == "region":
                items = []
                for region_name, region_queries in query.items():
                    region_count = 0
                    for region_query in region_queries:
                        try:
                            batch = parse_items(fetch(region_query), category)
                            for item in batch:
                                item["region"] = region_name
                            region_count += len(batch)
                            items.extend(batch)
                        except Exception as exc:
                            print(f"Region feed failed for {region_name}/{region_query}: {exc}")
                    print(f"region/{region_name}: {region_count} fresh stories")'''
if old_region_loop in text:
    text = text.replace(old_region_loop, new_region_loop)

old_build = 'f\'<category>{item["category"]}</category>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\','
new_build = 'f\'<category>{item["category"]}</category>\', f\'<region>{xml_escape(item.get("region", ""))}</region>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\','
if old_build in text:
    text = text.replace(old_build, new_build)

path.write_text(text, encoding="utf-8")
print("Patched collector: trusted-source allowlist, foreign-story routing to World, and existing NFL/Local/Regional behavior preserved.")
