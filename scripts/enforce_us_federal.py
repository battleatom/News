import html
import re
import xml.etree.ElementTree as ET

NEWS_FILE = "News"

# Clear U.S. federal-government signals. These can establish a U.S. federal
# story, but they no longer override a headline that is plainly about a foreign
# government, court, official, or country.
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
    "trump administration", "biden administration", "president trump", "president biden",
)

# These are commonly U.S. federal phrases in U.S.-focused feeds, but are not
# country-specific by themselves. They are only accepted when no foreign-country
# signal is present, unless the headline also has clear U.S. subject evidence.
US_FEDERAL_GENERIC = (
    "federal government", "federal judge", "federal court", "federal appeals court",
    "federal agency", "federal law", "federal lawsuit", "federal prosecutor",
    "federal prosecutors", "federal regulation", "federal rule", "federal funding",
    "supreme court",
)

# U.S.-subject terms that disambiguate a generic federal phrase when a foreign
# word is only contextual/comparative. Example: a U.S. federal appeals court
# comparing a Trump migrant-detention policy to Japanese American internment is
# still a U.S. Federal story; "Japanese" is not the story's jurisdiction.
US_SUBJECT_CONTEXT = (
    "donald trump", "trump", "joe biden", "biden", "white house",
    "migrant detention", "immigration policy", "immigration", "deportation",
    "ice detention", "border policy", "asylum policy", "american internment",
    "japanese american internment", "u.s. policy", "us policy",
)

FOREIGN_TERMS = (
    "brazil", "brazilian", "argentina", "argentine", "colombia", "mexico", "mexican",
    "canada", "canadian", "united kingdom", "britain", "british", "england", "london",
    "france", "french", "germany", "german", "italy", "italian", "spain", "spanish",
    "sweden", "swedish", "norway", "norwegian", "denmark", "danish", "finland", "finnish",
    "poland", "polish", "netherlands", "dutch", "belgium", "belgian", "austria", "austrian",
    "european union", "europe", "ukraine", "ukrainian", "russia", "russian", "moscow",
    "china", "chinese", "beijing", "japan", "japanese", "south korea", "korean",
    "india", "indian", "pakistan", "iran", "iranian", "israel", "israeli", "gaza",
    "palestine", "palestinian", "iraq", "iraqi", "syria", "syrian", "lebanon",
    "turkey", "turkish", "australia", "australian", "new zealand", "taiwan",
    "philippines", "indonesia", "south africa", "nigeria", "kenya", "egypt",
    "north korea", "united nations", "nato", "west bank",
)

# Named foreign-government signals catch stories whose headlines omit the country
# adjective. These are intentionally narrow and can be expanded as needed.
FOREIGN_FOCUS_TERMS = (
    "alexandre de moraes", "de moraes", "jair bolsonaro", "luiz inacio lula",
    "luiz inácio lula", "lula da silva", "brasilia", "brasília",
    "supreme federal court of brazil", "brazil supreme court",
)

LEGISLATION_SOURCE_TERMS = (
    "congress.gov", "congress gov", "federalregister.gov", "federal register",
    "nmlegis.gov", "new mexico legislature",
)

LEGISLATION_TITLE_PATTERNS = (
    r"\bh\.?\s*r\.?\s*\d+\b",
    r"\bs\.?\s*\d+\b",
    r"\bh\.?\s*j\.?\s*res\.?\s*\d+\b",
    r"\bs\.?\s*j\.?\s*res\.?\s*\d+\b",
    r"\bh\.?\s*con\.?\s*res\.?\s*\d+\b",
    r"\bs\.?\s*con\.?\s*res\.?\s*\d+\b",
)


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def has_any(text, terms):
    return any(term in text for term in terms)


def set_category(item, category):
    category_el = item.find("category")
    if category_el is None:
        category_el = ET.SubElement(item, "category")
    category_el.text = category


def is_official_legislation(item):
    title = clean(item.findtext("title"))
    source = clean(item.findtext("source"))
    link = clean(item.findtext("link"))
    official = clean(item.findtext("officialSource"))
    bill_number = clean(item.findtext("billNumber"))
    combined_source = f"{source} {link} {official}"

    if has_any(combined_source, LEGISLATION_SOURCE_TERMS):
        return True
    if bill_number:
        return True
    return any(re.search(pattern, title, flags=re.I) for pattern in LEGISLATION_TITLE_PATTERNS)


def federal_item_is_us(item):
    title = clean(item.findtext("title"))
    supporting = " ".join(
        clean(item.findtext(tag))
        for tag in ("description", "source", "whyMatters")
    )
    full_text = f"{title} {supporting}".strip()

    # The central headline subject wins over a foreign comparison/reference. A
    # generic U.S.-federal institution plus an unmistakably U.S. policy/actor is
    # enough to establish jurisdiction before inspecting incidental foreign terms.
    if has_any(title, US_FEDERAL_GENERIC) and has_any(title, US_SUBJECT_CONTEXT):
        return True

    # Headline subject wins. A headline explicitly about another country,
    # foreign court or foreign official cannot stay in U.S. Federal.
    if has_any(title, FOREIGN_TERMS) or has_any(title, FOREIGN_FOCUS_TERMS):
        return False

    # A clearly U.S.-federal headline is Federal.
    if has_any(title, US_FEDERAL_STRONG):
        return True

    # If the headline is not clearly U.S. and the story body is foreign-focused,
    # keep it out of Federal. This prevents generic phrases like "Supreme Court"
    # from turning foreign court stories into U.S. federal news.
    if has_any(full_text, FOREIGN_TERMS) or has_any(full_text, FOREIGN_FOCUS_TERMS):
        return False

    # Otherwise allow clear U.S. federal signals or generic federal phrases only
    # when no foreign signal is present anywhere in the story metadata.
    if has_any(full_text, US_FEDERAL_STRONG):
        return True
    return has_any(full_text, US_FEDERAL_GENERIC)


def main():
    tree = ET.parse(NEWS_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    moved_world = 0
    moved_legislation = 0
    kept_federal = 0

    for item in channel.findall("item"):
        category = clean(item.findtext("category"))
        if category != "federal":
            continue

        # Official legislative records are a dedicated product surface. They must
        # never remain in the general Federal news tab even if later verification
        # sees words such as Congress, House, Senate, or federal.
        if is_official_legislation(item):
            set_category(item, "legislation")
            moved_legislation += 1
            continue

        if federal_item_is_us(item):
            kept_federal += 1
            continue

        set_category(item, "world")
        region_el = item.find("region")
        if region_el is not None:
            region_el.text = ""
        moved_world += 1

    # Fail closed if an official legislative record somehow remains in Federal.
    leaked_legislation = [
        clean(i.findtext("title"))
        for i in channel.findall("item")
        if clean(i.findtext("category")) == "federal" and is_official_legislation(i)
    ]
    if leaked_legislation:
        raise SystemExit(
            "Federal integrity check failed; legislation still present: "
            + "; ".join(leaked_legislation[:10])
        )

    tree.write(NEWS_FILE, encoding="utf-8", xml_declaration=True)
    print(
        "Federal integrity filter kept "
        f"{kept_federal} U.S. federal stories, routed {moved_legislation} official legislative "
        f"record(s) to Legislation, and routed {moved_world} non-U.S./unclear story/stories out of Federal."
    )


if __name__ == "__main__":
    main()
