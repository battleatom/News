from pathlib import Path
import re

path = Path("scripts/update_news.py")
text = path.read_text(encoding="utf-8")

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

# X is intentionally NOT part of update_news.py's normal article pool. Its data
# is collected and clustered by enrich_x_issues.py after the normal feed is built,
# keeping the X signal layer separate from conventional news ranking.
text = re.sub(r'    "x": \[\n(?:.*\n)*?    \],\n', '', text, count=1)

# Keep X out of the normal collector sections; enrich_x_issues.py appends it later.
match = re.search(r'SECTIONS\s*=\s*\[[^\n]+\]', text)
if match:
    sections = match.group(0)
    sections = sections.replace('"x", ', '').replace(', "x"', '')
    text = text[:match.start()] + sections + text[match.end():]

# Support list-valued queries (including NFL) without breaking scalar queries.
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

# Ensure region-aware collector logic for older versions of update_news.py.
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

# Preserve region metadata in RSS output.
old_build = 'f\'<category>{item["category"]}</category>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\','
new_build = 'f\'<category>{item["category"]}</category>\', f\'<region>{xml_escape(item.get("region", ""))}</region>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\','
if old_build in text:
    text = text.replace(old_build, new_build)

path.write_text(text, encoding="utf-8")
print("Patched collector: preserved NFL, Local, and Regional improvements; X is handled by the dedicated signal enrichment step.")
