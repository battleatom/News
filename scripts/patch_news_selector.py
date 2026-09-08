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

old_sections = 'SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "nm", "local", "technology", "gaming", "military"]'
new_sections = 'SECTIONS = ["top", "underreported", "world", "us", "presidential", "federal", "nm", "local", "region", "technology", "gaming", "military"]'
text = text.replace(old_sections, new_sections)

# Regional queries intentionally emphasize strong regional/public-service outlets rather
# than simply searching a state name. Google News still supplies the freshness layer.
region_block = '''    "region": [
        "site:propublica.org Southwest Arizona Colorado New Mexico Nevada Utah OR site:statesnewsroom.com Southwest OR site:azmirror.com OR site:sourcenm.com OR site:coloradosun.com OR site:sltrib.com OR site:nevadanews.com",
        "site:latimes.com California OR site:calmatters.org OR site:oregoncapitalchronicle.com OR site:washingtonstatestandard.com OR site:statesnewsroom.com West",
        "site:coloradosun.com OR site:coloradonewsline.com OR site:utahnewsdispatch.com OR site:idahocapitalsun.com OR site:dailymontanan.com OR site:wyofile.com Mountain West",
        "site:statesnewsroom.com Midwest OR site:capitolnewsillinois.com OR site:indianacapitalchronicle.com OR site:iowacapitaldispatch.com OR site:michiganadvance.com OR site:minnesotareformer.com OR site:missouriindependent.com OR site:ohiocapitaljournal.com OR site:wisconsingexaminer.com",
        "site:statesnewsroom.com South OR site:texastribune.org OR site:virginiamercury.com OR site:ncnewsline.com OR site:tennesseelookout.com OR site:floridaphoenix.com OR site:georgiarecorder.com OR site:alabamareflector.com",
        "site:statesnewsroom.com Northeast OR site:newyorkfocus.com OR site:capital-star.com OR site:ctmirror.org OR site:commonwealthbeacon.org OR site:maine-morningstar.com OR site:njmonitor.com OR site:spotlightdelaware.org",
        "site:washingtonstatestandard.com OR site:oregoncapitalchronicle.com OR site:idahocapitalsun.com OR site:alaskabeacon.com OR site:statesnewsroom.com Northwest",
        "site:statesnewsroom.com Southeast OR site:floridaphoenix.com OR site:georgiarecorder.com OR site:alabamareflector.com OR site:ncnewsline.com OR site:scdailygazette.com OR site:tennesseelookout.com OR site:mississippitoday.org",
    ],'''
start = text.find('    "region": [')
if start != -1:
    end = text.find('    ],', start)
    if end != -1:
        end += len('    ],')
        text = text[:start] + region_block + text[end:]
else:
    anchor = '    "local": ['
    start = text.find(anchor)
    end = text.find('    ],', start)
    if start != -1 and end != -1:
        end += len('    ],')
        text = text[:end] + '\n' + region_block + text[end:]

# Make the collector accept list-valued queries while preserving existing behavior.
old_loop = '''    for category, query in QUERIES.items():
        try:
            items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories")
            all_items.extend(items)
        except Exception as exc:
            print(f"Feed failed for {category}: {exc}")'''
new_loop = '''    for category, query in QUERIES.items():
        queries = query if isinstance(query, list) else [query]
        category_items = []
        for q in queries:
            try:
                items = parse_items(fetch(q), category)
                category_items.extend(items)
            except Exception as exc:
                print(f"Feed failed for {category}/{q}: {exc}")
        print(f"{category}: {len(category_items)} fresh stories")
        all_items.extend(category_items)'''
if old_loop in text:
    text = text.replace(old_loop, new_loop)

old_explicit_loop = '''            if category == "local":
                items = []
                for local_query in LOCAL_QUERIES:
                    try:
                        batch = parse_items(fetch(local_query), category)
                        print(f"local/{local_query}: {len(batch)} fresh stories")
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Local feed failed for {local_query}: {exc}")
            else:
                items = parse_items(fetch(query), category)'''
new_explicit_loop = '''            if category == "local":
                items = []
                for local_query in LOCAL_QUERIES:
                    try:
                        batch = parse_items(fetch(local_query), category)
                        print(f"local/{local_query}: {len(batch)} fresh stories")
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Local feed failed for {local_query}: {exc}")
            elif category == "region":
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
                        print(f"Region feed failed for {region_name}: {exc}")
            else:
                items = parse_items(fetch(query), category)'''
if old_explicit_loop in text:
    text = text.replace(old_explicit_loop, new_explicit_loop)

if 'elif category == "region":' not in text:
    needle = '''            else:
                items = parse_items(fetch(query), category)'''
    replacement = '''            elif category == "region":
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
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Region feed failed for {region_name}: {exc}")
            else:
                items = parse_items(fetch(query), category)'''
    text = text.replace(needle, replacement, 1)

old_build = 'f\'<category>{item["category"]}</category>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\','
new_build = 'f\'<category>{item["category"]}</category>\', f\'<region>{xml_escape(item.get("region", ""))}</region>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\','
if old_build in text:
    text = text.replace(old_build, new_build)

old_selected = '''    selected_by_category = {category: select_category_stories([x for x in unique if x["category"] == category]) for category in SECTIONS[2:]}
    top = select_top_stories(top_unique)'''
new_selected = '''    selected_by_category = {}
    for category in SECTIONS[2:]:
        category_items = [x for x in unique if x["category"] == category]
        if category == "region":
            selected_by_category[category] = []
            for region_name in ("southwest", "west", "mountain", "midwest", "south", "northeast", "pacific-northwest", "southeast"):
                region_items = [x for x in category_items if x.get("region") == region_name]
                selected_by_category[category].extend(select_category_stories(region_items, limit=10))
        else:
            selected_by_category[category] = select_category_stories(category_items)
    top = select_top_stories(top_unique)'''
if old_selected in text:
    text = text.replace(old_selected, new_selected)

path.write_text(text, encoding="utf-8")
print("Patched collector: preserved Local and added source-focused regional news data.")
