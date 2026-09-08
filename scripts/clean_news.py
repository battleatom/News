import html
import re
import runpy
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
    "earthquake", "ruling", "court", "government", "president", "prime minister",
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


def is_vague_world_headline(item):
    if normalized(item.findtext("category")) != "world":
        return False
    headline = headline_without_source(item)
    if not headline:
        return True
    words = re.findall(r"[A-Za-z0-9]+", headline)
    lowered = headline.lower()
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
    if any(term in text for term in GAMING_BLOCK_TERMS):
        return True
    if any(term in source for term in GAMING_COMMERCE_SOURCES):
        return True
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
    removed_vague_world = 0

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
        kept.append(item)

    for item in items:
        channel.remove(item)
    for item in kept:
        channel.append(item)

    tree.write(NEWS_FILE, encoding="utf-8", xml_declaration=True)
    print(f"Removed {removed_gaming} gaming commerce/coupon items.")
    print(f"Removed {removed_paywall} ordinary-category paywall-source items.")
    print(f"Removed {removed_vague_world} vague World headlines.")
    print("Local stories retained after upstream geographic selection.")

    # The X collector's previous discovery query required Google News RSS to
    # return literal x.com destinations, which produces zero results in practice.
    # Broaden discovery to reporting that explicitly describes X conversations,
    # while keeping the downstream independent-reporting verification step.
    try:
        p = "scripts/enrich_x_issues.py"
        src = open(p, "r", encoding="utf-8").read()
        src = src.replace(
            'fetch(f"site:x.com {query} (trending OR viral OR discussion OR controversy)")',
            'fetch(f"{query} (\\\"on X\\\" OR \\\"on Twitter\\\" OR \\\"X users\\\" OR viral OR trending)")'
        )
        src = src.replace(
            'return "x.com/" in link.lower() or "twitter.com/" in link.lower() or bool(re.search(r"\\b(?:on|posted on|posts? on|from)\\s+(?:x|twitter)\\b", text))',
            'return bool(re.search(r"\\b(?:on|posted on|posts? on|from)\\s+(?:x|twitter)\\b", text)) or "x.com/" in link.lower() or "twitter.com/" in link.lower()'
        )
        ns = {"__name__": "__main__"}
        exec(compile(src, p, "exec"), ns, ns)
    except Exception as exc:
        print(f"X issue enrichment failed; retaining base feed: {exc}")


if __name__ == "__main__":
    main()
