from pathlib import Path

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

# X is a separate conversation-signal pool. The enrichment step clusters these
# indexed public X/Twitter results and deliberately does not invent post counts.
if '    "x": [' not in text:
    anchor = '    "underreported": '
    idx = text.find(anchor)
    if idx != -1:
        text = text[:idx] + '''    "x": [
        "site:x.com Trump OR White House OR Congress",
        "site:x.com world war OR conflict OR international",
        "site:x.com health medical FDA disease",
        "site:x.com entertainment movie music celebrity",
        "site:x.com AI technology Apple Google OpenAI",
        "site:x.com gaming PlayStation Xbox Nintendo",
        "site:x.com NFL NBA MLB soccer sports",
        "site:x.com economy stocks tariffs jobs business",
        "site:x.com science space NASA climate",
        "site:x.com breaking news developing viral",
    ],
''' + text[idx:]

old_sections = 'SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "nm", "local", "technology", "gaming", "military"]'
new_sections = 'SECTIONS = ["top", "nfl", "x", "underreported", "world", "us", "presidential", "federal", "nm", "local", "region", "technology", "gaming", "military"]'
text = text.replace(old_sections, new_sections)

region_block = '''    "region": {
        "southwest": ["Arizona news", "New Mexico news", "Colorado news", "Utah news", "Nevada news"],
        "west": ["California news", "Nevada news", "Oregon news", "Washington state news"],
        "mountain": ["Colorado news", "Utah news", "Idaho news", "Montana news", "Wyoming news"],
        "midwest": ["Illinois news", "Michigan news", "Ohio news", "Wisconsin news", "Minnesota news", "Iowa news", "Missouri news", "Indiana news"],
        "south": ["Texas news", "Oklahoma news", "Arkansas news", "Louisiana news", "Tennessee news", "Kentucky news", "Virginia news", "West Virginia news"],
        "northeast": ["New York news", "Pennsylvania news", "New Jersey news", "Connecticut news", "Massachusetts news", "New England news", "Maine news", "New Hampshire news", "Vermont news", "Rhode Island news"],
        "pacific-northwest": ["Washington state news", "Oregon news", "Idaho news", "Alaska news"],
        "southeast": ["Florida news", "Georgia news", "Alabama news", "South Carolina news", "North Carolina news", "Mississippi news", "Tennessee news"],
    },'''
start = text.find('    "region": [')
if start != -1:
    end = text.find('    ],', start)
    if end != -1:
        text = text[:start] + region_block + text[end + len('    ],'):]

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
print("Patched collector: added NFL and X conversation-signal feeds while preserving Local and Regional coverage.")
