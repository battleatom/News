from pathlib import Path

INDEX = Path("index.html")
UPDATE = Path("scripts/update_news.py")

text = UPDATE.read_text(encoding="utf-8")
text = text.replace(
    'if len(selected) == 10:\n            break\n    return selected\n\n\ndef select_underreported',
    'if len(selected) == 30:\n            break\n    return selected\n\n\ndef select_underreported',
    1,
)
text = text.replace(
    'if len(selected) == 12:\n            break\n    return selected\n\n\ndef select_category_stories(items, limit=10):',
    'if len(selected) == 30:\n            break\n    return selected\n\n\ndef select_category_stories(items, limit=30):',
    1,
)
text = text.replace(
    '"""Select up to 10 distinct stories, with Local queries treated as the geographic scope."""',
    '"""Select up to 30 distinct stories, with Local queries treated as the geographic scope."""',
    1,
)
text = text.replace('select_category_stories(region_items, limit=10)', 'select_category_stories(region_items, limit=30)', 1)
UPDATE.write_text(text, encoding="utf-8")

text = INDEX.read_text(encoding="utf-8")
marker = '<script id="load-more-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</script>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</script>'):]

# Load More behavior is JavaScript only. Styling belongs exclusively to
# styles/theme.css so this patch cannot override the authoritative theme.
script = r'''<script id="load-more-v1">
const STORIES_PER_PAGE = 10;
const loadCounts = {};

function paginatedNewsItems(items){
  const categoryItems = items.filter(item => (item.querySelector('category')?.textContent?.trim() || 'world') === active);
  let available = categoryItems;
  if(active === 'region') available = categoryItems.filter(item => (item.querySelector('region')?.textContent?.trim() || '') === detectedRegion);
  const count = Math.min(loadCounts[active] || STORIES_PER_PAGE, available.length);
  return {available, visible: available.slice(0, count), count};
}

const baseRenderWithPagination = render;
render = function(items){
  if(active === 'nfl') return baseRenderWithPagination(items);

  const data = paginatedNewsItems(items);
  baseRenderWithPagination(data.visible);
  const root = document.getElementById('news-feed');
  const section = root.querySelector('.section');
  if(!section) return;
  const countEl = section.querySelector('.section-header .count');
  if(countEl) countEl.textContent = `Showing ${data.count} of ${data.available.length} stories`;
  if(data.available.length <= data.count) return;
  const more = document.createElement('div');
  more.className = 'load-more-wrap';
  const button = document.createElement('button');
  button.className = 'load-more';
  const next = Math.min(data.count + STORIES_PER_PAGE, data.available.length);
  button.textContent = `Load 10 more (${next} of ${data.available.length})`;
  button.onclick = () => { loadCounts[active] = next; render(allItems); };
  more.appendChild(button);
  section.appendChild(more);
};
</script>'''

text = text.replace('</body>', script + '\n</body>', 1)
INDEX.write_text(text, encoding="utf-8")
print("Applied Load More pagination without injecting CSS that can override styles/theme.css.")
