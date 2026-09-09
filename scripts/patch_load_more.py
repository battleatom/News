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

# Make the existing NFL renderer honor the same per-tab count used by pagination.
text = text.replace(
    'allNfl.slice(0,10).forEach((item,i)=>',
    'allNfl.slice(0,Math.min((window.loadCounts?.nfl||10),allNfl.length)).forEach((item,i)=>',
    1,
)

# Load More must wrap canonicalRender because canonical tab clicks call that function
# directly. Wrapping only `render` leaves the control bypassed during normal tab use.
script = r'''<script id="load-more-v1">
const STORIES_PER_PAGE = 10;
window.loadCounts = window.loadCounts || {};
const loadCounts = window.loadCounts;

function paginatedNewsItems(items){
  const categoryItems = items.filter(item => (item.querySelector('category')?.textContent?.trim() || 'world') === active);
  let available = categoryItems;
  if(active === 'region') available = categoryItems.filter(item => (item.querySelector('region')?.textContent?.trim() || '') === detectedRegion);
  const count = Math.min(loadCounts[active] || STORIES_PER_PAGE, available.length);
  return {available, visible: available.slice(0, count), count};
}

function appendLoadMoreControl(data){
  const root = document.getElementById('news-feed');
  if(!root || data.available.length <= data.count) return;
  const section = root.querySelector('.section') || root;
  if(section.querySelector('.load-more-wrap')) return;
  const more = document.createElement('div');
  more.className = 'load-more-wrap';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'load-more';
  const next = Math.min(data.count + STORIES_PER_PAGE, data.available.length);
  button.textContent = `Load 10 more (${next} of ${data.available.length})`;
  button.onclick = () => {
    loadCounts[active] = next;
    canonicalRender(allItems);
  };
  more.appendChild(button);
  section.appendChild(more);
}

const baseCanonicalRenderWithPagination = canonicalRender;
canonicalRender = function(items){
  if(active === 'bookmarks' || active === 'boxoffice'){
    return baseCanonicalRenderWithPagination(items);
  }

  if(active === 'nfl'){
    const data = paginatedNewsItems(items);
    loadCounts.nfl = data.count;
    baseCanonicalRenderWithPagination(items);
    const nflHeader = [...document.querySelectorAll('.section-header .count')].find(el => el.closest('.section-header')?.querySelector('h2')?.textContent?.includes('NFL News'));
    if(nflHeader) nflHeader.textContent = `Showing ${data.count} of ${data.available.length}`;
    appendLoadMoreControl(data);
    return;
  }

  const data = paginatedNewsItems(items);
  baseCanonicalRenderWithPagination(data.visible);
  const root = document.getElementById('news-feed');
  const countEl = root?.querySelector('.section .section-header .count');
  if(countEl) countEl.textContent = `Showing ${data.count} of ${data.available.length} stories`;
  appendLoadMoreControl(data);
};

render = canonicalRender;
window.render = canonicalRender;
</script>'''

text = text.replace('</body>', script + '\n</body>', 1)
INDEX.write_text(text, encoding="utf-8")
print("Applied canonical Load More pagination with NFL support.")
