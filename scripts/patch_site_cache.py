from pathlib import Path

# Keep the page cache metadata current.
path = Path("index.html")
text = path.read_text(encoding="utf-8")
needle = '<meta charset="UTF-8">'
meta = '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">'
if meta not in text and needle in text:
    text = text.replace(needle, needle + meta, 1)
path.write_text(text, encoding="utf-8")

# Repair list-valued category queries in the collector. Technology, Gaming,
# Military, and NFL use multiple Google News searches. Passing the Python list
# directly to fetch() turns the whole list representation into one malformed
# search string and can leave those categories empty.
collector = Path("scripts/update_news.py")
source = collector.read_text(encoding="utf-8")
old = '''            else:
                items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
new = '''            else:
                queries = query if isinstance(query, list) else [query]
                items = []
                for q in queries:
                    try:
                        batch = parse_items(fetch(q), category)
                        print(f"{category}/{q}: {len(batch)} fresh stories")
                        items.extend(batch)
                    except Exception as exc:
                        print(f"Feed failed for {category}/{q}: {exc}")
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
if old in source:
    source = source.replace(old, new, 1)
elif 'queries = query if isinstance(query, list) else [query]' not in source:
    raise SystemExit('Could not locate list-query collector block in update_news.py')
collector.write_text(source, encoding="utf-8")
print("Patched cache metadata and list-valued category query handling.")
