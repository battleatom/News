from pathlib import Path

path = Path("scripts/update_news.py")
text = path.read_text(encoding="utf-8")

old_local = '    "local": "Farmington New Mexico OR San Juan County New Mexico OR Aztec New Mexico OR Bloomfield New Mexico OR Kirtland New Mexico OR Shiprock New Mexico OR Four Corners New Mexico",'
new_local = '''    "local": [
        "Farmington New Mexico",
        "San Juan County New Mexico",
        "Aztec New Mexico",
        "Bloomfield New Mexico",
        "Kirtland New Mexico",
        "Shiprock New Mexico",
        "Four Corners New Mexico",
    ],'''
if old_local in text:
    text = text.replace(old_local, new_local)

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

old_selector = '''def select_category_stories(items, limit=10):
    """Select up to 10 distinct stories, preferring publisher diversity but never letting it starve a category."""
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

    # Pass 2: fill the remaining slots. Multiple stories from a publisher are
    # acceptable; duplicate stories are not. This guarantees 10 whenever the
    # collector has at least 10 distinct stories for that category.
    for item in ranked:
        k = key(item)
        if not k or k in seen_keys:
            continue
        selected.append(item); seen_keys.add(k)
        if len(selected) == limit:
            break
    return selected'''
new_selector = '''def select_category_stories(items, limit=10):
    """Select up to 10 distinct stories, with a hard geographic gate for Local."""
    if items and items[0].get("category") == "local":
        local_terms = (
            "farmington", "san juan county", "san juan regional", "aztec, nm", "aztec nm",
            "aztec new mexico", "bloomfield, nm", "bloomfield nm", "bloomfield new mexico",
            "kirtland, nm", "kirtland nm", "kirtland new mexico", "shiprock", "navajo nation",
            "four corners", "san juan basin",
        )
        local_sources = (
            "farmington daily times", "daily times", "navajo times", "san juan county",
            "four corners", "new mexico", "krtm", "ksje",
        )
        items = [
            item for item in items
            if any(term in (item.get("title") or "").lower() for term in local_terms)
            or any(term in (item.get("source") or "").lower() for term in local_sources)
        ]

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

    # Pass 2: fill remaining slots with distinct stories.
    for item in ranked:
        k = key(item)
        if not k or k in seen_keys:
            continue
        selected.append(item); seen_keys.add(k)
        if len(selected) == limit:
            break
    return selected'''
if old_selector in text:
    text = text.replace(old_selector, new_selector)

path.write_text(text, encoding="utf-8")
print("Patched news collector with safe Local selection and category fill rules.")
