from pathlib import Path

path = Path("scripts/update_news.py")
text = path.read_text(encoding="utf-8")

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

# Also support the previous multi-query patch if the workflow has already run once.
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

old_selector_start = text.find('def select_category_stories(items, limit=10):')
old_selector_end = text.find('\n\ndef why_matters', old_selector_start)
if old_selector_start != -1 and old_selector_end != -1:
    new_selector = '''def select_category_stories(items, limit=10):
    """Select up to 10 distinct stories, with Local queries treated as the geographic scope."""
    if items and items[0].get("category") == "local":
        local_terms = (
            "farmington", "san juan county", "san juan regional", "aztec", "bloomfield",
            "kirtland", "shiprock", "navajo nation", "four corners", "san juan basin",
            "farmington daily times", "daily times", "navajo times", "krtm", "ksje",
        )
        outside_terms = (
            "california", "texas", "florida", "new york", "chicago", "atlanta",
            "phoenix", "denver", "las vegas", "albuquerque", "santa fe",
        )
        local_items = []
        for item in items:
            title = (item.get("title") or "").lower()
            source = (item.get("source") or "").lower()
            desc = (item.get("description") or "").lower()
            local_signal = any(term in title or term in source for term in local_terms)
            outside_signal = any(term in title for term in outside_terms)
            if local_signal and not outside_signal:
                local_items.append(item)
        # Prefer strongly identified local stories, but do not let publisher
        # diversity or a brittle second geography filter reduce the category.
        items = local_items

    ranked = sorted(items, key=lambda x: x["published"], reverse=True)
    selected, seen_keys, seen_sources = [], set(), set()

    # Pass 1: maximize publisher diversity.
    for item in ranked:
        k = key(item); source = source_key(item["source"] or "Unknown")
        if not k or k in seen_keys or source in seen_sources:
            continue
        selected.append(item); seen_keys.add(k); seen_sources.add(source)
        if len(selected) == limit:
            return selected

    # Pass 2: fill every remaining slot with distinct stories.
    for item in ranked:
        k = key(item)
        if not k or k in seen_keys:
            continue
        selected.append(item); seen_keys.add(k)
        if len(selected) == limit:
            break
    return selected'''
    text = text[:old_selector_start] + new_selector + text[old_selector_end:]

path.write_text(text, encoding="utf-8")
print("Patched Local collector to use broader local queries and reliable slot filling.")
