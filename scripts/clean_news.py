import html
import re
import xml.etree.ElementTree as ET

NEWS_FILE = "News"

GAMING_BLOCK_TERMS = (
    "coupon", "promo code", "promo codes", "discount code", "discount codes",
    "coupon code", "coupon codes", "deal of the day", "gaming deals",
    "game deals", "best deals", "price drop", "price drops", "sale price",
    "clearance", "affiliate", "sponsored content", "sponsored post",
)
GAMING_COMMERCE_SOURCES = (
    "slickdeals", "dealnews", "gamespot deals", "ign deals", "pc gamer deals",
    "tom's guide", "tomsguide", "techradar deals", "walmart", "best buy",
    "amazon", "newegg", "gamestop deals",
)
ORDINARY_PAYWALL_SOURCES = (
    "the new york times", "new york times", "wall street journal", "wsj",
    "bloomberg", "the washington post", "washington post",
)
WORLD_HEADLINE_EVENT_TERMS = (
    "attack", "attacks", "attacked", "strike", "strikes", "struck", "war",
    "ceasefire", "invasion", "invades", "missile", "missiles", "killed",
    "dies", "died", "election", "elections", "votes", "voted", "sanctions",
    "tariff", "tariffs", "crisis", "earthquake", "hurricane", "wildfire",
    "ruling", "court", "government", "president", "prime minister",
    "resigns", "resignation", "arrested", "arrests", "protest", "protests",
    "protesters", "agrees", "announces", "announced", "approves", "approved",
    "orders", "launches", "launch", "explosion", "explodes", "collapse", "collapsed",
)


def clean(value):
    value = html.unescape(value or "")
    return re.sub(r"<[^>]+>", " ", value)


def normalized(value):
    return re.sub(r"\s+", " ", clean(value)).strip().lower()


def headline_without_source(item):
    title = clean(item.findtext("title"))
    source = clean(item.findtext("source")).strip()
    if source:
        title = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", title, flags=re.I)
    return re.sub(r"\s+", " ", title).strip()


def description_without_source(item):
    desc = re.sub(r"\s+", " ", clean(item.findtext("description"))).strip()
    source = re.sub(r"\s+", " ", clean(item.findtext("source"))).strip()
    if source:
        desc = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", desc, flags=re.I)
    return desc.strip()


def story_key(item):
    title = re.sub(r"[^a-z0-9\s]", " ", headline_without_source(item).lower())
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by", "after", "new", "says", "said", "that", "this", "are", "was", "were", "has", "have", "had", "into", "over", "its", "their", "will", "amid", "more", "than"}
    return " ".join(w for w in title.split() if w not in stop)


def is_vague_world_headline(item):
    if normalized(item.findtext("category")) != "world":
        return False
    headline = headline_without_source(item)
    if not headline:
        return True
    words = re.findall(r"[A-Za-z0-9]+", headline)
    lowered = headline.lower()
    if re.fullmatch(r"(?:world|international)\s+news(?:\s+\d+)?", lowered):
        return True
    if re.fullmatch(r"(?:world|international)\s+(?:news\s+)?(?:\d+)", lowered):
        return True
    if len(words) <= 2:
        return True
    if len(words) <= 3 and not any(term in lowered for term in WORLD_HEADLINE_EVENT_TERMS):
        return True
    return False


def is_gaming_commerce(item):
    text = normalized(item.findtext("title")) + " " + normalized(item.findtext("description"))
    source = normalized(item.findtext("source"))
    return (
        any(term in text for term in GAMING_BLOCK_TERMS)
        or any(term in source for term in GAMING_COMMERCE_SOURCES)
        or bool(re.search(r"\b(coupon|promo|discount)\b", text))
        or bool(re.search(r"\b(save|off)\s+\$?\d+\b", text))
    )


def is_ordinary_paywall(item):
    if normalized(item.findtext("category")) in ("top", "underreported"):
        return False
    source = normalized(item.findtext("source"))
    return any(name in source for name in ORDINARY_PAYWALL_SOURCES)


def is_duplicate_underreported(item, seen_keys):
    if normalized(item.findtext("category")) != "underreported":
        return False
    k = story_key(item)
    if not k or k in seen_keys:
        return True
    seen_keys.add(k)
    return False


def is_malformed_item(item):
    """Reject actual RSS/list artifacts, not ordinary Google headline descriptions."""
    raw = re.sub(r"\s+", " ", clean(item.findtext("description"))).strip()
    title = headline_without_source(item)
    link = (item.findtext("link") or "").strip()
    if not title or not link:
        return True
    if re.search(r"(?:^|\s)#{1,6}\s*\[", raw):
        return True
    if re.search(r"\]\(https?://(?:news\.google\.com|www\.google\.com)/", raw, re.I):
        return True
    if raw and raw.count("https://news.google.com/rss/articles/") >= 2:
        return True
    return False


def suppress_repeated_description(item):
    """Hide headline+publisher boilerplate while preserving the actual story item."""
    desc_el = item.find("description")
    if desc_el is None:
        return False
    meaningful = description_without_source(item)
    title = headline_without_source(item)
    if not meaningful:
        desc_el.text = ""
        return True
    title_words = re.findall(r"[a-z0-9]+", title.lower())
    desc_words = re.findall(r"[a-z0-9]+", meaningful.lower())
    if not title_words:
        return False
    title_set = set(title_words)
    desc_set = set(desc_words)
    overlap = len(title_set & desc_set) / max(1, len(title_set))
    extra = [w for w in desc_words if w not in title_set]
    if overlap >= 0.85 and len(extra) <= 5:
        desc_el.text = ""
        return True
    return False


def main():
    tree = ET.parse(NEWS_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    items = channel.findall("item")
    kept = []
    removed_gaming = removed_paywall = removed_vague_world = 0
    removed_underreported_duplicates = removed_malformed = suppressed_descriptions = 0
    seen_underreported = set()

    for item in items:
        category = normalized(item.findtext("category"))
        if category == "gaming" and is_gaming_commerce(item):
            removed_gaming += 1
            continue
        if is_ordinary_paywall(item):
            removed_paywall += 1
            continue
        if is_vague_world_headline(item):
            removed_vague_world += 1
            continue
        if is_malformed_item(item):
            removed_malformed += 1
            continue
        if is_duplicate_underreported(item, seen_underreported):
            removed_underreported_duplicates += 1
            continue
        if suppress_repeated_description(item):
            suppressed_descriptions += 1
        kept.append(item)

    # Catastrophic-cleanup protection: never silently turn a healthy generated feed
    # into an empty or near-empty feed because of one bad filter rule.
    if len(items) >= 20 and len(kept) < max(10, int(len(items) * 0.10)):
        raise SystemExit(f"Cleanup safety stop: would reduce {len(items)} stories to {len(kept)}")

    for item in items:
        channel.remove(item)
    for item in kept:
        channel.append(item)
    tree.write(NEWS_FILE, encoding="utf-8", xml_declaration=True)

    print(f"Removed {removed_gaming} gaming commerce/coupon items.")
    print(f"Removed {removed_paywall} ordinary-category paywall-source items.")
    print(f"Removed {removed_vague_world} vague World headlines.")
    print(f"Removed {removed_malformed} actual malformed/list artifacts.")
    print(f"Suppressed {suppressed_descriptions} headline-only RSS descriptions without deleting stories.")
    print(f"Removed {removed_underreported_duplicates} duplicate Underreported stories.")
    print(f"Final cleanup retained {len(kept)} of {len(items)} stories.")


if __name__ == "__main__":
    main()
