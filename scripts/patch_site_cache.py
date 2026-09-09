from pathlib import Path

# Keep the page cache metadata current.
path = Path("index.html")
text = path.read_text(encoding="utf-8")
needle = '<meta charset="UTF-8">'
meta = '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">'
if meta not in text and needle in text:
    text = text.replace(needle, needle + meta, 1)
path.write_text(text, encoding="utf-8")

collector = Path("scripts/update_news.py")
source = collector.read_text(encoding="utf-8")

# Federal needs topic-diverse discovery. A single broad Google News query can be
# swallowed by one court/redistricting event and leave only a handful of stories
# after the strict U.S.-federal filter and event dedupe.
old_federal_query = '    "federal": "US Congress OR federal government OR Supreme Court",'
new_federal_query = '''    "federal": [
        "US Congress Senate House legislation committee federal government",
        "US Supreme Court federal appeals court federal judge",
        "DOJ FBI DHS federal agency government policy",
        "EPA FTC SEC FCC IRS federal regulation rule",
        "US Treasury State Department federal government agency",
        "federal budget spending government shutdown Congress",
    ],'''
if old_federal_query in source:
    source = source.replace(old_federal_query, new_federal_query, 1)

# Technology, Gaming, Military, and NFL are configured with several search
# phrases. Never stringify a Python list into the Google News query. Federal is
# intentionally handled as separate searches below so one event cannot dominate.
old = '''            else:
                items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
combined = '''            else:
                combined_query = " OR ".join(f"({q})" for q in query) if isinstance(query, list) else query
                items = parse_items(fetch(combined_query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
if old in source:
    source = source.replace(old, combined, 1)
elif 'combined_query = " OR ".join' not in source and 'category == "federal" and isinstance(query, list)' not in source:
    raise SystemExit('Could not locate list-query collector block in update_news.py')

# Local source names are deliberately narrow: these are established Four Corners
# publishers/stations, not a general weakening of the trusted-source gate.
local_trust = '''\nTRUSTED_LOCAL_SOURCE_TOKENS = (\n    "tri city record", "ksje", "navajo times", "durango herald", "the journal",\n)\nTRUSTED_SOURCE_TOKENS = tuple(sorted(set(TRUSTED_SOURCE_TOKENS) | set(TRUSTED_LOCAL_SOURCE_TOKENS)))\n'''
if 'TRUSTED_LOCAL_SOURCE_TOKENS = (' not in source:
    anchor = '\nTRUSTED_SPORTS_SOURCE_TOKENS = (' if '\nTRUSTED_SPORTS_SOURCE_TOKENS = (' in source else '\nFOREIGN_ONLY_TERMS = ('
    if anchor not in source:
        raise SystemExit('Could not locate trusted-source insertion point in update_news.py')
    source = source.replace(anchor, local_trust + anchor, 1)

# Add established sports publishers without weakening the general source gate.
# Use full normalized source names (for example "nfl com"), not a broad "nfl"
# token that could accidentally trust unrelated sites.
sports_trust = '''\nTRUSTED_SPORTS_SOURCE_TOKENS = (\n    "espn", "nfl com", "cbs sports", "nbc sports", "fox sports",\n    "yahoo sports", "sports illustrated", "pro football talk",\n)\nTRUSTED_SOURCE_TOKENS = tuple(sorted(set(TRUSTED_SOURCE_TOKENS) | set(TRUSTED_SPORTS_SOURCE_TOKENS)))\n'''
if 'TRUSTED_SPORTS_SOURCE_TOKENS = (' not in source:
    anchor = '\nFOREIGN_ONLY_TERMS = ('
    if anchor not in source:
        raise SystemExit('Could not locate FOREIGN_ONLY_TERMS in update_news.py')
    source = source.replace(anchor, sports_trust + anchor, 1)

# Let the final local geography selector recognize established Four Corners
# outlets. The fallback searches below are location-constrained, so this does not
# turn unrelated statewide stories into Local stories.
source = source.replace(
    '            "farmington daily times", "daily times", "navajo times", "krtm", "ksje",\n',
    '            "farmington daily times", "daily times", "navajo times", "krtm", "ksje",\n            "tri-city record", "tri city record", "durango herald", "the journal",\n',
    1,
)

# Normal Google News category searches can be dominated by publishers that are
# intentionally rejected by the trusted-source gate. If a sparse category is
# thin, query established publishers directly rather than weakening source quality.
fallbacks = '''\nTRUSTED_CATEGORY_FALLBACKS = {\n    "local": [\n        ("Tri-City Record", "site:tricityrecordnm.com (Farmington OR \\\"San Juan County\\\" OR Aztec OR Bloomfield OR Kirtland OR Shiprock OR \\\"Four Corners\\\")"),\n        ("KSJE", "site:ksje.com (Farmington OR \\\"San Juan County\\\" OR Aztec OR Bloomfield OR Kirtland OR Shiprock OR \\\"Four Corners\\\")"),\n        ("Navajo Times", "site:navajotimes.com (Shiprock OR Farmington OR \\\"San Juan County\\\" OR \\\"Four Corners\\\")"),\n        ("Durango Herald", "site:durangoherald.com (Farmington OR Shiprock OR Aztec OR \\\"San Juan County\\\" OR \\\"Four Corners\\\")"),\n        ("The Journal", "site:the-journal.com (Farmington OR Shiprock OR Cortez OR \\\"Four Corners\\\")"),\n    ],\n    "nfl": [\n        ("ESPN", "site:espn.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("NFL.com", "site:nfl.com/news (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("CBS Sports", "site:cbssports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("NBC Sports", "site:nbcsports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("Fox Sports", "site:foxsports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("Yahoo Sports", "site:sports.yahoo.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n    ],\n    "technology": [\n        ("The Verge", "site:theverge.com (AI OR technology OR cybersecurity OR Microsoft OR Apple OR Google OR Nvidia)"),\n        ("Ars Technica", "site:arstechnica.com (AI OR technology OR security OR software OR chips OR computing)"),\n        ("TechCrunch", "site:techcrunch.com (AI OR technology OR cybersecurity OR software OR startups)"),\n        ("Wired", "site:wired.com (AI OR technology OR cybersecurity OR computing)"),\n        ("Tom's Hardware", "site:tomshardware.com (Nvidia OR AMD OR Intel OR GPU OR CPU OR hardware)"),\n    ],\n    "gaming": [\n        ("IGN", "site:ign.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo OR PC gaming)"),\n        ("GameSpot", "site:gamespot.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo)"),\n        ("PC Gamer", "site:pcgamer.com (gaming OR PC gaming OR Nvidia OR AMD OR Steam)"),\n        ("Nintendo Life", "site:nintendolife.com (Nintendo OR Switch OR gaming OR games)"),\n        ("Polygon", "site:polygon.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo)"),\n    ],\n}\n'''
if 'TRUSTED_CATEGORY_FALLBACKS = {' not in source:
    anchor = '\nCATEGORY_WEIGHT = {'
    if anchor not in source:
        raise SystemExit('Could not locate CATEGORY_WEIGHT in update_news.py')
    source = source.replace(anchor, fallbacks + anchor, 1)
else:
    # Upgrade existing fallback dictionaries with Local and/or NFL when needed.
    start = source.find('TRUSTED_CATEGORY_FALLBACKS = {')
    end = source.find('\nCATEGORY_WEIGHT = {', start)
    fallback_block = source[start:end] if start != -1 and end != -1 else ''
    if '    "local": [' not in fallback_block:
        local_block = '''    "local": [\n        ("Tri-City Record", "site:tricityrecordnm.com (Farmington OR \\\"San Juan County\\\" OR Aztec OR Bloomfield OR Kirtland OR Shiprock OR \\\"Four Corners\\\")"),\n        ("KSJE", "site:ksje.com (Farmington OR \\\"San Juan County\\\" OR Aztec OR Bloomfield OR Kirtland OR Shiprock OR \\\"Four Corners\\\")"),\n        ("Navajo Times", "site:navajotimes.com (Shiprock OR Farmington OR \\\"San Juan County\\\" OR \\\"Four Corners\\\")"),\n        ("Durango Herald", "site:durangoherald.com (Farmington OR Shiprock OR Aztec OR \\\"San Juan County\\\" OR \\\"Four Corners\\\")"),\n        ("The Journal", "site:the-journal.com (Farmington OR Shiprock OR Cortez OR \\\"Four Corners\\\")"),\n    ],\n'''
        source = source.replace('TRUSTED_CATEGORY_FALLBACKS = {\n', 'TRUSTED_CATEGORY_FALLBACKS = {\n' + local_block, 1)
    start = source.find('TRUSTED_CATEGORY_FALLBACKS = {')
    end = source.find('\nCATEGORY_WEIGHT = {', start)
    fallback_block = source[start:end] if start != -1 and end != -1 else ''
    if '    "nfl": [' not in fallback_block:
        nfl_block = '''    "nfl": [\n        ("ESPN", "site:espn.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("NFL.com", "site:nfl.com/news (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("CBS Sports", "site:cbssports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("NBC Sports", "site:nbcsports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("Fox Sports", "site:foxsports.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n        ("Yahoo Sports", "site:sports.yahoo.com/nfl (NFL OR football OR injury OR trade OR roster OR game)"),\n    ],\n'''
        source = source.replace('TRUSTED_CATEGORY_FALLBACKS = {\n', 'TRUSTED_CATEGORY_FALLBACKS = {\n' + nfl_block, 1)

# Local has its own collection branch, so it must run its fallback pool there
# rather than relying on the generic branch below.
old_local_collection = '''            if category == "local":
                items = []
                for local_query in LOCAL_QUERIES:
                    try:
                        batch = parse_items(fetch(local_query), category)
                        print(f"local/{local_query}: {len(batch)} fresh stories")
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Local feed failed for {local_query}: {exc}")'''
new_local_collection = '''            if category == "local":
                items = []
                for local_query in LOCAL_QUERIES:
                    try:
                        batch = parse_items(fetch(local_query), category)
                        print(f"local/{local_query}: {len(batch)} fresh stories")
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Local feed failed for {local_query}: {exc}")
                usable_count = len(select_category_stories(items, limit=30))
                if usable_count < 10:
                    for fallback_source, fallback_query in TRUSTED_CATEGORY_FALLBACKS.get("local", []):
                        try:
                            batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                            items.extend(batch)
                            usable_count = len(select_category_stories(items, limit=30))
                            print(f"local fallback/{fallback_source}: {len(batch)} accepted; {usable_count} usable local stories")
                            if usable_count >= 15:
                                break
                        except Exception as exc:
                            print(f"Local fallback failed for {fallback_source}: {exc}")'''
if old_local_collection in source:
    source = source.replace(old_local_collection, new_local_collection, 1)
elif 'local fallback/{fallback_source}' not in source:
    raise SystemExit('Could not install Four Corners fallbacks in Local collector branch')

old_combined = '''            else:
                combined_query = " OR ".join(f"({q})" for q in query) if isinstance(query, list) else query
                items = parse_items(fetch(combined_query), category)
                own_count = sum(1 for item in items if item.get("category") == category)
                if category in TRUSTED_CATEGORY_FALLBACKS and own_count < 10:
                    for fallback_source, fallback_query in TRUSTED_CATEGORY_FALLBACKS[category]:
                        try:
                            batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                            items.extend(batch)
                            own_count = sum(1 for item in items if item.get("category") == category)
                            print(f"{category} fallback/{fallback_source}: {len(batch)} accepted; {own_count} category stories")
                            if own_count >= 20:
                                break
                        except Exception as exc:
                            print(f"{category} fallback failed for {fallback_source}: {exc}")
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
new_combined = '''            else:
                if category == "federal" and isinstance(query, list):
                    items = []
                    for federal_query in query:
                        try:
                            batch = parse_items(fetch(federal_query), category)
                            items.extend(batch)
                            print(f"federal/{federal_query}: {len(batch)} fresh stories")
                        except Exception as exc:
                            print(f"Federal feed failed for {federal_query}: {exc}")
                else:
                    combined_query = " OR ".join(f"({q})" for q in query) if isinstance(query, list) else query
                    items = parse_items(fetch(combined_query), category)
                own_count = sum(1 for item in items if item.get("category") == category)
                usable_count = len(select_category_stories(items, limit=30)) if category == "local" else own_count
                if category in TRUSTED_CATEGORY_FALLBACKS and usable_count < 10:
                    for fallback_source, fallback_query in TRUSTED_CATEGORY_FALLBACKS[category]:
                        try:
                            batch = parse_items(fetch(fallback_query), category, source_override=fallback_source)
                            items.extend(batch)
                            own_count = sum(1 for item in items if item.get("category") == category)
                            usable_count = len(select_category_stories(items, limit=30)) if category == "local" else own_count
                            print(f"{category} fallback/{fallback_source}: {len(batch)} accepted; {usable_count} usable category stories")
                            target = 15 if category == "local" else 20
                            if usable_count >= target:
                                break
                        except Exception as exc:
                            print(f"{category} fallback failed for {fallback_source}: {exc}")
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
if old_combined in source:
    source = source.replace(old_combined, new_combined, 1)
elif 'category == "federal" and isinstance(query, list)' not in source:
    raise SystemExit('Could not install diversified Federal and trusted category fallbacks in update_news.py')

# A product/platform/industry story is not foreign affairs merely because it
# mentions Japan, China, etc. Keep clear Tech/Gaming industry coverage in its
# category unless the story also contains geopolitical/government signals.
old_route = '''def should_route_to_world(title, description, category):
    if category == "world":
        return False
    text = f"{title} {description}".lower()
    foreign_hits = sum(1 for term in FOREIGN_ONLY_TERMS if term in text)
    us_hits = sum(1 for term in US_CONTEXT_TERMS if term in text)
    return foreign_hits >= 2 and us_hits == 0
'''
new_route = '''def should_route_to_world(title, description, category):
    if category == "world":
        return False
    text = f"{title} {description}".lower()
    if category in ("gaming", "technology"):
        domain_terms = (
            "gaming", "video game", "playstation", "xbox", "nintendo", "switch", "steam", "game studio",
            "technology", "software", "hardware", "artificial intelligence", " ai ", "chip", "semiconductor",
            "gpu", "cpu", "nvidia", "amd", "intel", "microsoft", "apple", "google", "android", "iphone",
            "cybersecurity", "data breach", "cloud computing",
        )
        geopolitical_terms = (
            "government", "president", "prime minister", "parliament", "election", "military", "war",
            "sanction", "tariff", "diplomat", "embassy", "protest", "attack", "invasion", "ceasefire",
            "foreign ministry", "defense ministry", "national security law",
        )
        padded = f" {text} "
        if any(term in padded for term in domain_terms) and not any(term in text for term in geopolitical_terms):
            return False
    foreign_hits = sum(1 for term in FOREIGN_ONLY_TERMS if term in text)
    us_hits = sum(1 for term in US_CONTEXT_TERMS if term in text)
    return foreign_hits >= 2 and us_hits == 0
'''
if old_route in source:
    source = source.replace(old_route, new_route, 1)
elif 'domain_terms = (' not in source:
    raise SystemExit('Could not update World routing for Tech/Gaming')

collector.write_text(source, encoding="utf-8")
print("Patched cache metadata, diversified Federal discovery, ran trusted Four Corners fallbacks in Local, and preserved domain-aware World routing.")
