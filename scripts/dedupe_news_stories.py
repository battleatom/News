import difflib
import html
import re
import xml.etree.ElementTree as ET

NEWS_FILE = "News"
STOP_WORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "with", "is", "as", "at", "from", "by",
    "after", "before", "new", "says", "said", "that", "this", "are", "was", "were", "has", "have", "had",
    "into", "over", "its", "their", "will", "amid", "more", "than", "what", "know", "here", "latest",
    "update", "updates", "report", "reports", "news", "breaking", "today", "officials", "according"
}
GENERIC_TOPIC_WORDS = {
    "president", "presidential", "trump", "white", "house", "administration", "government", "politics",
    "congress", "senate", "democrats", "republicans", "republican", "democrat", "political", "washington",
    "federal", "official", "officials", "country", "state", "states", "america", "american"
}
GAMING_GENERIC_WORDS = {
    "game", "games", "gaming", "video", "player", "players", "nintendo", "switch", "playstation", "xbox",
    "steam", "pc", "direct", "showcase", "trailer", "teaser", "console", "consoles"
}
GAMING_EVENT_GROUPS = {
    "announcement": {"announced", "announce", "announces", "revealed", "reveal", "reveals", "confirmed", "confirm", "confirmation", "unveiled", "unveil"},
    "marketing": {"teaser", "trailer", "direct", "showcase", "presentation", "exclusive"},
    "release": {"launch", "launched", "release", "released", "delay", "delayed", "cancelled", "canceled"},
    "product_change": {"shutdown", "closure", "acquisition", "acquired", "gameplay", "beta", "demo", "update", "expansion"},
}

US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida",
    "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska",
    "nevada", "new hampshire", "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee", "texas",
    "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming", "district of columbia"
}

# State-centered federal disputes often generate many slightly different headlines
# from the same event. Keep one representative Federal story instead of allowing
# one state/case to dominate the category.
FEDERAL_STATE_EVENT_GROUPS = {
    "redistricting": {"redistricting", "map", "maps", "district", "districts", "congressional"},
    "elections": {"election", "elections", "voting", "voter", "voters", "ballot", "ballots"},
    "immigration": {"immigration", "migrant", "migrants", "border", "deportation", "deportations", "asylum"},
    "abortion": {"abortion", "abortions", "reproductive"},
}


def clean(value):
    value = html.unescape(value or "")
    return re.sub(r"<[^>]+>", " ", value)


def title_without_source(item):
    title = clean(item.findtext("title"))
    source = clean(item.findtext("source")).strip()
    if source:
        title = re.sub(rf"\s+(?:[-–—|:]\s*)?{re.escape(source)}\s*$", "", title, flags=re.I)
    title = re.sub(
        r"\s+(?:[-–—|:]\s*)?(?:AP News|Reuters|NBC News|CBS News|ABC News|CNN|BBC|NPR|USA Today|The Washington Post|The New York Times)\s*$",
        "", title, flags=re.I,
    )
    return re.sub(r"\s+", " ", title).strip()


def tokens(item):
    text = re.sub(r"[^a-z0-9\s]", " ", title_without_source(item).lower())
    # Preserve single-digit model/sequel/week numbers. They are often the detail
    # that distinguishes one gaming, technology, or sports story from another.
    return set(w for w in text.split() if w not in STOP_WORDS and (len(w) > 1 or w.isdigit()))


def content_tokens(item):
    return tokens(item) - GENERIC_TOPIC_WORDS


def gaming_event_groups(item):
    ts = content_tokens(item)
    return {name for name, terms in GAMING_EVENT_GROUPS.items() if ts & terms}


def same_gaming_event(a, b):
    """Catch the same named gaming announcement without merging a whole showcase."""
    ta, tb = content_tokens(a), content_tokens(b)
    shared = ta & tb
    if len(shared) < 2:
        return False
    if not (gaming_event_groups(a) & gaming_event_groups(b)):
        return False
    named_shared = {
        w for w in shared
        if not any(w in terms for terms in GAMING_EVENT_GROUPS.values())
        and w not in GAMING_GENERIC_WORDS
    }
    # Example: Persona 6 coverage shares the named subject "persona" and sequel
    # number "6", while two unrelated Nintendo Direct announcements do not.
    return len(named_shared) >= 2


def title_states(item):
    text = title_without_source(item).lower()
    return {state for state in US_STATE_NAMES if re.search(rf"\b{re.escape(state)}\b", text)}


def federal_state_event_groups(item):
    ts = tokens(item)
    return {name for name, terms in FEDERAL_STATE_EVENT_GROUPS.items() if ts & terms}


def same_federal_state_event(a, b):
    """Collapse repeated coverage of the same state-centered federal dispute."""
    shared_states = title_states(a) & title_states(b)
    if not shared_states:
        return False
    shared_groups = federal_state_event_groups(a) & federal_state_event_groups(b)
    if not shared_groups:
        return False

    # Redistricting/map stories are especially repetitive and easy to identify by
    # state + event family. For other event families, require additional shared
    # meaningful title language so unrelated cases in the same state are preserved.
    if "redistricting" in shared_groups:
        return True

    ta, tb = content_tokens(a), content_tokens(b)
    state_words = {w for state in shared_states for w in state.split()}
    shared_specific = (ta & tb) - state_words
    shared_specific -= set().union(*FEDERAL_STATE_EVENT_GROUPS.values())
    return len(shared_specific) >= 2


def very_close_title(a, b, minimum_common=5, ratio=0.94):
    ta, tb = tokens(a), tokens(b)
    common = len(ta & tb)
    if common < minimum_common:
        return False
    raw_a = title_without_source(a).lower()
    raw_b = title_without_source(b).lower()
    if len(raw_a) < 35 or len(raw_b) < 35:
        return False
    return difflib.SequenceMatcher(None, raw_a, raw_b).ratio() >= ratio


def same_story(a, b):
    ca = clean(a.findtext("category")).strip()
    cb = clean(b.findtext("category")).strip()
    if ca != cb:
        return False
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    if ta == tb:
        return True

    common = len(ta & tb)
    smaller = min(len(ta), len(tb))

    # Sports, technology and gaming headlines naturally reuse many category words.
    # The old generic 65% overlap rule collapsed whole NFL weeks and product events.
    # Use exact/near-exact title matching here, plus the dedicated gaming event rule.
    if ca == "nfl":
        return very_close_title(a, b, minimum_common=5, ratio=0.94)
    if ca == "technology":
        return very_close_title(a, b, minimum_common=5, ratio=0.95)
    if ca == "gaming":
        if same_gaming_event(a, b):
            return True
        return very_close_title(a, b, minimum_common=5, ratio=0.95)
    if ca == "federal":
        if same_federal_state_event(a, b):
            return True
        fa, fb = content_tokens(a), content_tokens(b)
        federal_common = len(fa & fb)
        federal_smaller = min(len(fa), len(fb))
        # Keep clearly identical federal events, but preserve distinct court
        # cases, agency actions and congressional stories.
        if federal_common >= 5 and federal_smaller >= 6 and federal_common / federal_smaller >= 0.78:
            return True
        return very_close_title(a, b, minimum_common=5, ratio=0.92)

    if smaller >= 5 and common / smaller >= 0.90:
        return True

    ca_tokens, cb_tokens = content_tokens(a), content_tokens(b)
    content_common = len(ca_tokens & cb_tokens)
    content_smaller = min(len(ca_tokens), len(cb_tokens))
    if ca == "presidential":
        if content_common < 3:
            return False
        if content_smaller >= 4 and content_common / content_smaller >= 0.60:
            return True
    else:
        if content_common >= 4 and content_smaller >= 5 and content_common / content_smaller >= 0.65:
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


def looks_english(item):
    text = f"{clean(item.findtext('title'))} {clean(item.findtext('description'))}".strip()
    if not text:
        return False
    non_latin = sum(1 for ch in text if any((lo <= ord(ch) <= hi) for lo, hi in (
        (0x0400, 0x052F), (0x0600, 0x06FF), (0x0900, 0x097F), (0x3040, 0x30FF),
        (0x3400, 0x9FFF), (0x0370, 0x03FF), (0x0590, 0x05FF),
    )))
    letters = sum(1 for ch in text if ch.isalpha())
    if letters and non_latin / letters > 0.12:
        return False
    latin_words = re.findall(r"[A-Za-z]{2,}", text.lower())
    if not latin_words:
        return False
    common_english = {"the", "and", "of", "to", "in", "for", "on", "with", "is", "that", "from", "by", "as", "at", "this", "new", "news"}
    if len(latin_words) >= 12 and not (set(latin_words) & common_english):
        return False
    return True


def main():
    tree = ET.parse(NEWS_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")
    items = channel.findall("item")
    kept = []
    seen_links = set()
    removed_exact = removed_language = removed_similar = 0
    for item in items:
        if not looks_english(item):
            removed_language += 1
            continue
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
    print(f"Removed {removed_language} clearly non-English stories.")
    print(f"Removed {removed_exact} exact-link duplicate stories.")
    print(f"Removed {removed_similar} same-category near-duplicate stories across sources.")
    print(f"Final feed contains {len(kept)} story items after language and cross-source deduplication.")


if __name__ == "__main__":
    main()
