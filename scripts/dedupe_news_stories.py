import difflib
import html
import re
import xml.etree.ElementTree as ET

NEWS_FILE = "News"
STOP_WORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by",
    "after", "before", "new", "says", "said", "that", "this", "are", "was", "were", "has", "have", "had",
    "into", "over", "its", "their", "will", "amid", "more", "than", "what", "know", "here", "latest",
    "update", "updates", "report", "reports"
}

def clean(value):
    value = html.unescape(value or "")
    return re.sub(r"<[^>]+>", " ", value)

def title_without_source(item):
    title = clean(item.findtext("title"))
    source = clean(item.findtext("source")).strip()
    if source:
        title = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", title, flags=re.I)
    # Google News can leave a publisher/domain suffix even when <source> differs.
    title = re.sub(r"\s+(?:[-–—|:]\s*)?(?:AP News|Reuters|NBC News|CBS News|ABC News|CNN|BBC|NPR|USA Today|The Washington Post|The New York Times)\s*$", "", title, flags=re.I)
    return re.sub(r"\s+", " ", title).strip()

def tokens(item):
    text = re.sub(r"[^a-z0-9\s]", " ", title_without_source(item).lower())
    return set(w for w in text.split() if w not in STOP_WORDS and len(w) > 1)

def same_story(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    common = len(ta & tb)
    smaller = min(len(ta), len(tb))
    if smaller >= 5 and common / smaller >= 0.90:
        return True
    sa = " ".join(sorted(ta))
    sb = " ".join(sorted(tb))
    if common >= 5 and difflib.SequenceMatcher(None, sa, sb).ratio() >= 0.86:
        return True
    raw_a = title_without_source(a).lower()
    raw_b = title_without_source(b).lower()
    if len(raw_a) >= 45 and len(raw_b) >= 45 and difflib.SequenceMatcher(None, raw_a, raw_b).ratio() >= 0.91 and common >= 5:
        return True
    return False

def main():
    tree = ET.parse(NEWS_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")
    items = channel.findall("item")
    # The feed is already ordered by editorial priority: Top, Underreported, then categories.
    # Keep the first occurrence so an event represented in multiple outlets/categories has one card.
    kept = []
    seen_links = set()
    removed_exact = 0
    removed_similar = 0
    for item in items:
        link = clean(item.findtext("link")).strip()
        if link and link in seen_links:
            removed_exact += 1
            continue
        if any(same_story(item, prior) for prior in kept):
            removed_similar += 1
            continue
        if link:
            seen_links.add(link)
        kept.append(item)
    for item in items:
        channel.remove(item)
    for item in kept:
        channel.append(item)
    tree.write(NEWS_FILE, encoding="utf-8", xml_declaration=True)
    print(f"Removed {removed_exact} exact-link duplicate stories.")
    print(f"Removed {removed_similar} near-duplicate stories across sources/categories.")
    print(f"Final feed contains {len(kept)} story items after cross-source deduplication.")

if __name__ == "__main__":
    main()
