from pathlib import Path

# Cache metadata is intentionally simple and idempotent.
page = Path('index.html')
text = page.read_text(encoding='utf-8')
needle = '<meta charset="UTF-8">'
meta = '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">'
if meta not in text and needle in text:
    text = text.replace(needle, needle + meta, 1)
page.write_text(text, encoding='utf-8')

# The collector is now maintained by the canonical selector/diversity/public-interest
# patches that run immediately before and after this step. Older versions of this
# script repeatedly rewrote the same blocks and became brittle once Legislation was
# added. Verify the established protections instead of rewriting already-canonical code.
collector = Path('scripts/update_news.py')
source = collector.read_text(encoding='utf-8')

required = {
    'diverse Federal queries': 'US Supreme Court federal appeals court federal judge',
    'trusted category fallbacks': 'TRUSTED_CATEGORY_FALLBACKS = {',
    'Four Corners local fallback': 'local fallback/{fallback_source}',
    'trusted local sources': 'TRUSTED_LOCAL_SOURCE_TOKENS = (',
    'trusted sports sources': 'TRUSTED_SPORTS_SOURCE_TOKENS = (',
    'domain-aware World routing': 'domain_terms = (',
}
missing = [label for label, marker in required.items() if marker not in source]
if missing:
    raise SystemExit('Collector maintenance verification failed; missing: ' + ', '.join(missing))

print('Verified cache metadata, diversified Federal discovery, trusted Local/category fallbacks, and domain-aware World routing.')
