from pathlib import Path
import re

path = Path("scripts/update_news.py")
text = path.read_text(encoding="utf-8")

TRUSTED_SOURCE_ALIASES = [
    "reuters", "associated press", "ap", "bbc", "npr", "pbs", "afp", "france 24", "france24",
    "deutsche welle", "dw", "the guardian", "sky news", "al jazeera", "euronews", "cbc", "nhk",
    "abc australia", "australian broadcasting corporation", "aap", "swissinfo", "rfi",
    "cnn", "nbc news", "abc news", "cbs news", "fox news", "usa today", "new york times",
    "washington post", "wall street journal", "wsj", "los angeles times", "chicago tribune",
    "boston globe", "politico", "axios", "the hill", "newsweek", "time", "usatoday",
    "bloomberg", "cnbc", "forbes", "yahoo news", "yahoo finance",
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

def source_is_trusted(source):
    s = re.sub(r"[^a-z0-9]+", " ", (source or "").lower()).strip()
    if not s:
        return False
    padded = f" {s} "
    return any(s == token or f" {token} " in padded for token in TRUSTED_SOURCE_TOKENS)


def should_route_to_world(title, description, category):
    if category == "world":
        return False
    text = f"{title} {description}".lower()
    foreign_hits = sum(1 for term in FOREIGN_ONLY_TERMS if term in text)
    us_hits = sum(1 for term in US_CONTEXT_TERMS if term in text)
    return foreign_hits >= 2 and us_hits == 0

# These helpers must exist in the generated collector itself. The patch script's
# own definitions are not visible when update_news.py is executed as a process.
generated_helpers = """\n\nTRUSTED_SOURCE_TOKENS = %r\nFOREIGN_ONLY_TERMS = %r\nUS_CONTEXT_TERMS = %r\n\ndef source_is_trusted(source):\n    s = re.sub(r\"[^a-z0-9]+\", \" \", (source or \"\").lower()).strip()\n    if not s:\n        return False\n    padded = f\" {s} \"\n    return any(s == token or f\" {token} \" in padded for token in TRUSTED_SOURCE_TOKENS)\n\ndef should_route_to_world(title, description, category):\n    if category == \"world\":\n        return False\n    text = f\"{title} {description}\".lower()\n    foreign_hits = sum(1 for term in FOREIGN_ONLY_TERMS if term in text)\n    us_hits = sum(1 for term in US_CONTEXT_TERMS if term in text)\n    return foreign_hits >= 2 and us_hits == 0\n""" % (TRUSTED_SOURCE_TOKENS, FOREIGN_ONLY_TERMS, US_CONTEXT_TERMS)

# Keep the helper definitions directly in update_news.py, before parse_items uses them.
if "def source_is_trusted(source):" not in text:
    anchor = "\ndef parse_date(value):"
    if anchor not in text:
        raise SystemExit("Could not locate parse_date() in update_news.py")
    text = text.replace(anchor, generated_helpers + anchor, 1)

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

# Install the source gate without relying on names defined in this patch process.
old_source = '''        source = source_override or clean(source_el.text if source_el is not None else "")
        if not source_is_trusted(source):
            continue
        if should_route_to_world(title, desc, category):
            category = "world"
'''
new_source = '''        source = source_override or clean(source_el.text if source_el is not None else "")
        if not source_is_trusted(source):
            continue
        item_category = "world" if should_route_to_world(title, desc, category) else category
'''
if old_source in text:
    text = text.replace(old_source, new_source, 1)
else:
    source_anchor = '        source = source_override or clean(source_el.text if source_el is not None else "")\n'
    if source_anchor in text and 'if not source_is_trusted(source):' not in text:
        text = text.replace(source_anchor, new_source, 1)

# Make the result use the per-item category so one foreign story cannot relabel an entire feed.
old_result = '''        result.append({"title": title, "link": link, "description": desc, "pubDate": pub,
                       "published": published, "source": source, "category": category})'''
new_result = '''        result.append({"title": title, "link": link, "description": desc, "pubDate": pub,
                       "published": published, "source": source, "category": item_category})'''
if old_result in text:
    text = text.replace(old_result, new_result, 1)

# Support list-valued queries (including NFL) without breaking scalar queries in older collector versions.
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
print("Patched collector: trusted-source validation, per-story World routing, and existing NFL/Local/Regional behavior preserved.")
