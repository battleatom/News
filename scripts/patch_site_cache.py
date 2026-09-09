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

# Technology, Gaming, Military, and NFL are configured with several search
# phrases. Never stringify a Python list into the Google News query. Combine the
# phrases into one valid OR search so the normal pass stays quick.
old = '''            else:
                items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
combined = '''            else:
                combined_query = " OR ".join(f"({q})" for q in query) if isinstance(query, list) else query
                items = parse_items(fetch(combined_query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
if old in source:
    source = source.replace(old, combined, 1)
elif 'combined_query = " OR ".join' not in source:
    raise SystemExit('Could not locate list-query collector block in update_news.py')

# Normal Google News category searches can be dominated by publishers that are
# intentionally rejected by the trusted-source gate. If Tech or Gaming is thin,
# query established publishers directly rather than weakening source quality.
fallbacks = '''\nTRUSTED_CATEGORY_FALLBACKS = {\n    "technology": [\n        ("The Verge", "site:theverge.com (AI OR technology OR cybersecurity OR Microsoft OR Apple OR Google OR Nvidia)"),\n        ("Ars Technica", "site:arstechnica.com (AI OR technology OR security OR software OR chips OR computing)"),\n        ("TechCrunch", "site:techcrunch.com (AI OR technology OR cybersecurity OR software OR startups)"),\n        ("Wired", "site:wired.com (AI OR technology OR cybersecurity OR computing)"),\n        ("Tom's Hardware", "site:tomshardware.com (Nvidia OR AMD OR Intel OR GPU OR CPU OR hardware)"),\n    ],\n    "gaming": [\n        ("IGN", "site:ign.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo OR PC gaming)"),\n        ("GameSpot", "site:gamespot.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo)"),\n        ("PC Gamer", "site:pcgamer.com (gaming OR PC gaming OR Nvidia OR AMD OR Steam)"),\n        ("Nintendo Life", "site:nintendolife.com (Nintendo OR Switch OR gaming OR games)"),\n        ("Polygon", "site:polygon.com (gaming OR video games OR PlayStation OR Xbox OR Nintendo)"),\n    ],\n}\n'''
if 'TRUSTED_CATEGORY_FALLBACKS = {' not in source:
    anchor = '\nCATEGORY_WEIGHT = {'
    if anchor not in source:
        raise SystemExit('Could not locate CATEGORY_WEIGHT in update_news.py')
    source = source.replace(anchor, fallbacks + anchor, 1)

old_combined = '''            else:
                combined_query = " OR ".join(f"({q})" for q in query) if isinstance(query, list) else query
                items = parse_items(fetch(combined_query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
new_combined = '''            else:
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
if old_combined in source:
    source = source.replace(old_combined, new_combined, 1)
elif 'category in TRUSTED_CATEGORY_FALLBACKS and own_count < 10' not in source:
    raise SystemExit('Could not install trusted category fallbacks in update_news.py')

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
elif 'A product/platform/industry story' not in source and 'domain_terms = (' not in source:
    raise SystemExit('Could not update World routing for Tech/Gaming')

collector.write_text(source, encoding="utf-8")
print("Patched cache metadata, trusted Tech/Gaming fallbacks, and domain-aware World routing.")
