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

style_marker = '<style id="load-more-style-v1">'
while style_marker in text:
    start = text.find(style_marker)
    end = text.find('</style>', start)
    if end == -1:
        break
    text = text[:start] + text[end + len('</style>'):]

# The live NFL renderer is installed immediately before this patch and used to
# hard-limit itself to 10 stories. Make it honor the same count as Load More.
text = text.replace(
    'allNfl.slice(0,10).forEach((item,i)=>',
    'allNfl.slice(0,Math.min((window.loadCounts?.nfl||10),allNfl.length)).forEach((item,i)=>',
    1,
)

style = r'''<style id="load-more-style-v1">
.load-more-wrap{display:flex;justify-content:center;width:100%;padding:18px 12px 8px;box-sizing:border-box}
.load-more{appearance:none;border:1px solid #cbd5e1;border-radius:999px;background:#fff;color:#0f172a;padding:11px 20px;font:inherit;font-size:12px;font-weight:800;cursor:pointer;box-shadow:0 2px 8px rgba(15,23,42,.08)}
.load-more:active{transform:translateY(1px)}
</style>'''
text = text.replace('</head>', style + '\n</head>', 1)

# Load More wraps canonicalRender because canonical tab clicks call that function
# directly. For NFL, place the control after the NFL News list rather than inside
# the live-score section so it is actually visible beneath the articles.
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
  if(!root) return;
  root.querySelectorAll('.load-more-wrap').forEach(el => el.remove());
  if(data.available.length <= data.count) return;

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

  if(active === 'nfl'){
    // renderNflLive places NFL News after the live-score section. Appending to
    // root here guarantees the control is directly below the news articles.
    root.appendChild(more);
  }else{
    const section = root.querySelector('.section') || root;
    section.appendChild(more);
  }
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
    const nflHeaders = [...document.querySelectorAll('.section-header')];
    const nflNewsHeader = nflHeaders.find(el => el.querySelector('h2')?.textContent?.trim() === 'NFL News');
    const countEl = nflNewsHeader?.querySelector('.count');
    if(countEl) countEl.textContent = `Showing ${data.count} of ${data.available.length}`;
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
print("Applied visible canonical Load More pagination with dynamic NFL support.")
