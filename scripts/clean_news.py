import html
import re
import xml.etree.ElementTree as ET

NEWS_FILE = "News"

# Commerce/affiliate material that should never appear in Gaming & Computing.
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

# Sources that commonly put substantial portions of their reporting behind a
# subscription. They are not removed from Top Stories/Underreported, where a
# major exclusive can still be important, but ordinary category pages prefer
# freely accessible alternatives when possible.
ORDINARY_PAYWALL_SOURCES = (
    "the new york times", "new york times", "wall street journal", "wsj",
    "bloomberg", "the washington post", "washington post",
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
    # Strong shopping/affiliate patterns that routinely slip through broad RSS searches.
    if re.search(r"\b(coupon|promo|discount)\b", text):
        return True
    if re.search(r"\b(save|off)\s+\$?\d+\b", text):
        return True
    return False


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

    for item in items:
        category = normalized(item.findtext("category"))
        if category == "gaming" and is_gaming_commerce(item):
            removed_gaming += 1
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


if __name__ == "__main__":
    main()
