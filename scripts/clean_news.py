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

# Local is specifically the Farmington / San Juan County / Four Corners area.
# Keep this filter aligned with the collector: do not use generic "New Mexico"
# as a Local signal because that admits statewide stories that belong in NM.
LOCAL_TITLE_TERMS = (
    "farmington", "san juan county", "san juan regional", "aztec, nm", "aztec nm",
    "aztec new mexico", "bloomfield, nm", "bloomfield nm", "bloomfield new mexico",
    "kirtland, nm", "kirtland nm", "kirtland new mexico", "shiprock", "navajo nation",
    "four corners", "san juan basin",
)
LOCAL_SOURCE_TERMS = (
    "farmington daily times", "daily times", "navajo times", "san juan county",
    "four corners", "new mexico", "krtm", "ksje",
)
LOCAL_BLOCKED_TERMS = (
    "new york", "new jersey", "pennsylvania", "oklahoma", "texas", "colorado",
    "california", "arizona", "utah", "missouri", "arkansas", "kansas", "nebraska",
    "louisiana", "florida", "georgia", "alabama", "tennessee", "north carolina",
    "south carolina", "virginia", "west virginia", "ohio", "michigan", "illinois",
    "indiana", "wisconsin", "minnesota", "iowa", "north dakota", "south dakota",
    "montana", "wyoming", "idaho", "washington", "oregon", "nevada", "mississippi",
    "kentucky", "maryland", "massachusetts", "connecticut", "rhode island", "vermont",
    "new hampshire", "maine", "delaware", "district of columbia", "washington, d.c.",
    "washington dc",
)


def clean(value):
    value = html.unescape(value or "")
    return re.sub(r"<[^>]+>", " ", value)


def normalized(value):
    return re.sub(r"\s+", " ", clean(value)).strip().lower()


def is_gaming_commerce(item):
    text = normalized(item.findtext("title")) + " " + normalized(item.findtext("description"))
    source = normalized(item.findtext("source"))
    if any(term in text for term in GAMING_BLOCK_TERMS):
        return True
    if any(term in source for term in GAMING_COMMERCE_SOURCES):
        return True
    if re.search(r"\b(coupon|promo|discount)\b", text):
        return True
    if re.search(r"\b(save|off)\s+\$?\d+\b", text):
        return True
    return False


def is_local_item(item):
    title = normalized(item.findtext("title"))
    source = normalized(item.findtext("source"))

    # Locality is determined from the headline or known local publisher, not
    # from the description. Descriptions frequently mention unrelated places.
    title_local = any(term in title for term in LOCAL_TITLE_TERMS)
    source_local = any(term in source for term in LOCAL_SOURCE_TERMS)
    if not (title_local or source_local):
        return False

    # If the headline itself names an outside state and does not name a local
    # Four Corners place, reject it. This prevents broad Google News matches.
    title_blocked = any(term in title for term in LOCAL_BLOCKED_TERMS)
    if title_blocked and not title_local:
        return False
    return True


def is_ordinary_paywall(item):
    category = normalized(item.findtext("category"))
    if category in ("top", "underreported"):
        return False
    source = normalized(item.findtext("source"))
    return any(name in source for name in ORDINARY_PAYWALL_SOURCES)


def main():
    tree = ET.parse(NEWS_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        return

    items = channel.findall("item")
    kept = []
    removed_gaming = 0
    removed_paywall = 0
    removed_nonlocal = 0

    for item in items:
        category = normalized(item.findtext("category"))
        if category == "gaming" and is_gaming_commerce(item):
            removed_gaming += 1
            continue
        if category == "local" and not is_local_item(item):
            removed_nonlocal += 1
            continue
        if is_ordinary_paywall(item):
            removed_paywall += 1
            continue
        kept.append(item)

    for item in items:
        channel.remove(item)
    for item in kept:
        channel.append(item)

    tree.write(NEWS_FILE, encoding="utf-8", xml_declaration=True)
    print(f"Removed {removed_gaming} gaming commerce/coupon items.")
    print(f"Removed {removed_paywall} ordinary-category paywall-source items.")
    print(f"Removed {removed_nonlocal} non-local stories from Local.")


if __name__ == "__main__":
    main()
