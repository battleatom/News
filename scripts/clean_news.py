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
        title = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", title).strip()


def description_without_source(item):
    """Return the RSS description with a trailing publisher/source label removed."""
    desc = re.sub(r"\s+", " ", clean(item.findtext("description"))).strip()
    source = re.sub(r"\s+", " ", clean(item.findtext("source"))).strip()
    if source:
        desc = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", desc, flags=re.IGNORECASE)
    return desc.strip()


def story_key(item):
    title = headline_without_source(item).lower()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
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
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9'’.-]*(?:\s+[A-Za-z0-9][A-Za-z0-9'’.-]*){0,2}", headline):
        return True
    return False


def is_gaming_commerce(item):
    text = normalized(item.findtext("title")) + " " + normalized(item.findtext("description"))
    source = normalized(item.findtext("source"))
    if any(term in text for term in GAMING_BLOCK_TERMS): return True
    if any(term in source for term in GAMING_COMMERCE_SOURCES): return True
    if re.search(r"\b(coupon|promo|discount)\b", text): return True
    if re.search(r"\b(save|off)\s+\$?\d+\b", text): return True
    return False


def is_ordinary_paywall(item):
    category = normalized(item.findtext("category"))
    if category in ("top", "underreported"):
        return False
    source = normalized(item.findtext("source"))
    return any(name in source for name in ORDINARY_PAYWALL_SOURCES)


def is_duplicate_underreported(item, seen_keys):
    if normalized(item.findtext("category")) != "underreported": return False
    k = story_key(item)
    if not k: return True
    if k in seen_keys: return True
    seen_keys.add(k)
    return False


def is_malformed_description(item):
    """Reject feed artifacts that render as markdown/headline metadata instead of article information."""
    title = headline_without_source(item)
    raw_desc = clean(item.findtext("description"))
    if not raw_desc.strip():
        return True
    d = re.sub(r"\s+", " ", raw_desc).strip()

    # Google News occasionally exposes a markdown-formatted result/list as the description.
    if re.search(r"(?:^|\s)#{1,6}\s*\[", d):
        return True
    if re.search(r"\]\(https?://(?:news\.google\.com|www\.google\.com)/", d, re.I):
        return True

    # Google News commonly emits only "headline + publisher" as description text.
    # Strip the publisher first; otherwise a long publisher name can make the
    # description look long enough to evade the repeated-headline check.
    meaningful = description_without_source(item)
    if not meaningful:
        return True

    title_norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    meaningful_norm = re.sub(r"[^a-z0-9]+", " ", meaningful.lower()).strip()
    if title_norm and meaningful_norm == title_norm:
        return True

    title_words = re.findall(r"[a-z0-9]+", title_norm)
    desc_words = re.findall(r"[a-z0-9]+", meaningful_norm)
    if title_words:
        title_set = set(title_words)
        desc_set = set(desc_words)
        overlap = len(title_set & desc_set) / max(1, len(title_set))
        # If almost all description words simply repeat the headline and there is
        # little additional text, there is no useful article summary to display.
        extra_words = [w for w in desc_words if w not in title_set]
        if overlap >= 0.85 and len(extra_words) <= 5:
            return True

    # Reject obvious metadata-only descriptions even when the source omitted the title.
    if re.fullmatch(r"(?:https?://\S+|[A-Za-z0-9 .,'’&-]+)\s*(?:\|\s*[A-Za-z0-9 .,'’&-]+)?", meaningful) and len(desc_words) <= 8:
        return True
    return False


def main():
    tree = ET.parse(NEWS_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None: return
    items = channel.findall("item")
    kept = []
    removed_gaming = removed_paywall = removed_vague_world = removed_underreported_duplicates = removed_malformed = 0
    seen_underreported = set()
    for item in items:
        category = normalized(item.findtext("category"))
        if category == "gaming" and is_gaming_commerce(item):
            removed_gaming += 1; continue
        if is_ordinary_paywall(item):
            removed_paywall += 1; continue
        if is_vague_world_headline(item):
            removed_vague_world += 1; continue
        if is_malformed_description(item):
            removed_malformed += 1; continue
        if is_duplicate_underreported(item, seen_underreported):
            removed_underreported_duplicates += 1; continue
        kept.append(item)
    for item in items: channel.remove(item)
    for item in kept: channel.append(item)
    tree.write(NEWS_FILE, encoding="utf-8", xml_declaration=True)
    print(f"Removed {removed_gaming} gaming commerce/coupon items.")
    print(f"Removed {removed_paywall} ordinary-category paywall-source items.")
    print(f"Removed {removed_vague_world} vague World headlines.")
    print(f"Removed {removed_malformed} malformed/metadata-only article descriptions.")
    print(f"Removed {removed_underreported_duplicates} duplicate Underreported stories.")
    print("Local stories retained after upstream geographic selection.")

if __name__ == "__main__": main()
