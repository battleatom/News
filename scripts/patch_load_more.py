from pathlib import Path

INDEX = Path("index.html")
UPDATE = Path("scripts/update_news.py")

# Keep a larger pool in the generated RSS so the browser can reveal more
# stories without another network request. The UI still starts at 10.
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
text = text.replace(
    'select_category_stories(region_items, limit=10)',
    'select_category_stories(region_items, limit=30)',
    1,
)
UPDATE.write_text(text, encoding="utf-8")

# Add client-side pagination after all existing render patches. This works for
# every category, including the location-aware Regional tab, while leaving the
# existing article renderer and Local geographic filtering intact.
text = INDEX.read_text(encoding="utf-8")
marker = '<script id="load-more-v1">'
while marker in text:
    start = text.find(marker)
    end = text.find('</script>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</script>'):]

script = r'''<script id="load-more-v1">
const STORIES_PER_PAGE = 10;
const loadCounts = {};

function paginatedNewsItems(items){
  const categoryItems = items.filter(item => (item.querySelector('category')?.textContent?.trim() || 'world') === active);
  let available = categoryItems;
  if(active === 'region'){
    available = categoryItems.filter(item => (item.querySelector('region')?.textContent?.trim() || '') === detectedRegion);
  }
  const count = Math.min(loadCounts[active] || STORIES_PER_PAGE, available.length);
  return {available, visible: available.slice(0, count), count};
}

const baseRenderWithPagination = render;
render = function(items){
  const data = paginatedNewsItems(items);
  baseRenderWithPagination(data.visible);

  const root = document.getElementById('news-feed');
  const section = root.querySelector('.section');
  if(!section) return;

  const countEl = section.querySelector('.section-header .count');
  if(countEl){
    const locationNote = active === 'region' && typeof detectedLocation !== 'undefined' && detectedLocation ? ' · ' + detectedLocation : '';
    countEl.textContent = `Showing ${data.count} of ${data.available.length} stories${locationNote}`;
  }

  if(data.available.length <= data.count) return;

  const more = document.createElement('div');
  more.className = 'load-more-wrap';
  const button = document.createElement('button');
  button.className = 'load-more';
  const next = Math.min(data.count + STORIES_PER_PAGE, data.available.length);
  button.textContent = `Load 10 more (${next} of ${data.available.length})`;
  button.onclick = () => {
    loadCounts[active] = next;
    render(allItems);
  };
  more.appendChild(button);
  // Keep the control at the bottom of the page/section, after all stories.
  section.appendChild(more);
};
</script>'''

css = r'''<style id="load-more-style-v1">
.load-more-wrap{display:flex;justify-content:center;padding:20px 10px 6px}
.load-more{appearance:none;border:1px solid #d5dae2;border-radius:999px;background:#fff;color:#344054;padding:10px 18px;font-size:11px;font-weight:750;cursor:pointer;box-shadow:0 1px 2px rgba(16,24,40,.05)}
.load-more:hover{background:#f5f6f8;border-color:#c5cad3}
.load-more:active{transform:translateY(1px)}
@media(max-width:600px){.load-more-wrap{padding:18px 5px 4px}.load-more{width:100%;padding:10px 14px;font-size:10.5px}}
</style>'''

text = text.replace('</head>', css + '</head>', 1)
text = text.replace('</body>', script + '</body>', 1)
INDEX.write_text(text, encoding="utf-8")
print("Added 10-at-a-time Load More pagination and placed the control at the bottom of each news section.")
