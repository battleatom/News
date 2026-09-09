import html
import re
import xml.etree.ElementTree as ET

NEWS_FILE = "News"

# Clear U.S. federal-government signals. These are strong enough to keep a story
# in the Federal Government tab even when another country is mentioned.
US_FEDERAL_STRONG = (
    "united states", "u.s.", "u.s. federal", "us federal", "american federal",
    "white house", "congress", "senate", "house of representatives", "capitol hill",
    "scotus", "u.s. supreme court", "us supreme court", "supreme court of the united states",
    "department of justice", "justice department", "doj", "fbi", "federal bureau of investigation",
    "department of homeland security", "homeland security", "dhs", "pentagon",
    "u.s. treasury", "us treasury", "treasury department", "state department", "department of state",
    "federal reserve", "federal trade commission", "ftc", "federal communications commission", "fcc",
    "securities and exchange commission", "sec", "environmental protection agency", "epa",
    "internal revenue service", "irs", "fema", "centers for disease control", "cdc",
    "health and human services", "hhs", "department of education", "department of labor",
    "department of energy", "department of commerce", "department of agriculture",
    "immigration and customs enforcement", "ice", "customs and border protection", "cbp",
    "bureau of alcohol tobacco firearms", "atf", "drug enforcement administration", "dea",
)

# These are commonly U.S. federal phrases in U.S.-focused feeds, but are not
# country-specific by themselves. They are only accepted when no foreign-country
# signal is present.
US_FEDERAL_GENERIC = (
    "federal government", "federal judge", "federal court", "federal appeals court",
    "federal agency", "federal law", "federal lawsuit", "federal prosecutor",
    "federal prosecutors", "federal regulation", "federal rule", "federal funding",
    "supreme court",
)

FOREIGN_TERMS = (
    "brazil", "brazilian", "argentina", "argentine", "colombia", "mexico", "mexican",
    "canada", "canadian", "united kingdom", "britain", "british", "england", "london",
    "france", "french", "germany", "german", "italy", "italian", "spain", "spanish",
    "european union", "europe", "ukraine", "ukrainian", "russia", "russian", "moscow",
    "china", "chinese", "beijing", "japan", "japanese", "south korea", "korean",
    "india", "indian", "pakistan", "iran", "iranian", "israel", "israeli", "gaza",
    "palestine", "palestinian", "iraq", "iraqi", "syria", "syrian", "lebanon",
    "turkey", "turkish", "australia", "australian", "new zealand", "taiwan",
    "philippines", "indonesia", "south africa", "nigeria", "kenya", "egypt",
    "north korea", "united nations", "nato", "west bank",
)


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def federal_item_is_us(item):
    text = " ".join(
        clean(item.findtext(tag))
        for tag in ("title", "description", "source", "whyMatters")
    )
    if any(term in text for term in US_FEDERAL_STRONG):
        return True
    if any(term in text for term in FOREIGN_TERMS):
        return False
    return any(term in text for term in US_FEDERAL_GENERIC)


def main():
    tree = ET.parse(NEWS_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    moved = 0
    kept_federal = 0
    for item in channel.findall("item"):
        category = clean(item.findtext("category"))
        if category != "federal":
            continue
        if federal_item_is_us(item):
            kept_federal += 1
            continue
        category_el = item.find("category")
        if category_el is None:
            category_el = ET.SubElement(item, "category")
        category_el.text = "world"
        region_el = item.find("region")
        if region_el is not None:
            region_el.text = ""
        moved += 1

    tree.write(NEWS_FILE, encoding="utf-8", xml_declaration=True)
    print(f"Federal US-only filter kept {kept_federal} U.S. federal stories and routed {moved} non-U.S./unclear stories to World.")


if __name__ == "__main__":
    main()
