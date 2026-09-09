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
# Military, and NFL are configured with several search phrases. The collector
# previously passed the Python list itself to Google News, producing a malformed
# query. Combine the phrases into one valid OR query so each category needs only
# one RSS request and the 15-minute updater stays fast.
collector = Path("scripts/update_news.py")
source = collector.read_text(encoding="utf-8")
old = '''            else:
                items = parse_items(fetch(query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
new = '''            else:
                combined_query = " OR ".join(f"({q})" for q in query) if isinstance(query, list) else query
                items = parse_items(fetch(combined_query), category)
            print(f"{category}: {len(items)} fresh stories before dedupe")'''
if old in source:
    source = source.replace(old, new, 1)
elif 'combined_query = " OR ".join' not in source:
    raise SystemExit('Could not locate list-query collector block in update_news.py')
collector.write_text(source, encoding="utf-8")
print("Patched cache metadata and combined list-valued category queries.")
