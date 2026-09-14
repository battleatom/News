#!/usr/bin/env python3
"""Final quality guard for ranked Entertainment cards.

Keeps the existing ranking order, removes low-value roundup/review-compilation cards,
and collapses same-person/same-event duplicate cards into one lead while preserving
the removed card as supporting coverage. Box Office is not touched.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

NEWS = Path("News")
MIN_HEALTHY = 15

LOW_VALUE = (
    "reviews compilation",
    "review compilation",
    "movie reviews compilation",
    "photo gallery",
    "celebrity photos",
    "see celebrity photos",
    "all the looks",
    "every look",
    "seen and heard at every",
    "what to watch",
    "best dressed",
)

EVENT_GROUPS = {
    "relationship": ("divorce", "split", "splits", "marriage", "married", "wife", "husband", "dating", "boyfriend", "girlfriend", "relationship"),
    "legal": ("arrest", "arrested", "detained", "charged", "court", "lawsuit", "sued", "investigation"),
    "death-health": ("dies", "died", "death", "dead", "hospitalized", "cancer", "illness", "injury"),
    "controversy": ("backlash", "controversy", "criticism", "criticized", "scandal", "apology"),
    "career": ("cast", "casting", "joins", "starring", "premiere", "tour", "album", "concert", "series", "movie", "film"),
}

NAME_NOISE = {
    "The Hollywood Reporter", "USA Today", "NBC News", "CBS News", "ABC News",
    "Entertainment Weekly", "Rolling Stone", "New York", "Los Angeles", "United States",
    "Prime Video", "HBO Max",
}
STOP = {
    "the", "and", "for", "with", "from", "after", "before", "about", "amid", "into",
    "star", "actor", "actress", "celebrity", "entertainment", "news", "exclusive",
}


def title(node: ET.Element) -> str:
    return (node.findtext("title") or "").strip()


def groups(text: str) -> set[str]:
    low = text.lower()
    return {name for name, terms in EVENT_GROUPS.items() if any(term in low for term in terms)}


def people(text: str) -> set[str]:
    out: set[str] = set()
    for phrase in re.findall(r"\b(?:[A-Z][A-Za-z'’.-]+)(?:\s+(?:[A-Z][A-Za-z'’.-]+)){1,3}\b", text):
        cleaned = phrase.strip(" -–—:,.")
        if cleaned in NAME_NOISE:
            continue
        words = cleaned.split()
        # Prefer plausible personal names and avoid long headline fragments.
        if 2 <= len(words) <= 3 and all(len(w.strip("'’.-")) >= 2 for w in words):
            out.add(cleaned.lower())
    return out


def terms(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z0-9]+", text.lower())
        if len(w) >= 3 and w not in STOP
    }


def same_event(a: ET.Element, b: ET.Element) -> bool:
    at, bt = title(a), title(b)
    ag, bg = groups(at), groups(bt)
    shared_people = people(at) & people(bt)
    if shared_people and ag & bg:
        return True

    ta, tb = terms(at), terms(bt)
    if not ta or not tb:
        return False
    shared = ta & tb
    smaller = min(len(ta), len(tb))
    return len(shared) >= 5 or (len(shared) >= 4 and len(shared) / max(1, smaller) >= 0.55)


def low_value(node: ET.Element) -> bool:
    low = title(node).lower()
    return any(term in low for term in LOW_VALUE)


def add_related(keeper: ET.Element, duplicate: ET.Element) -> None:
    holder = keeper.find("relatedArticles")
    if holder is None:
        holder = ET.SubElement(keeper, "relatedArticles")

    dup_link = (duplicate.findtext("link") or "").strip()
    existing = {(x.findtext("link") or "").strip() for x in holder.findall("article")}
    if dup_link and dup_link in existing:
        return

    art = ET.SubElement(holder, "article")
    for tag in ("title", "link", "source"):
        el = ET.SubElement(art, tag)
        el.text = (duplicate.findtext(tag) or "").strip()


def main() -> None:
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("News RSS is missing channel")

    entertainment = [
        n for n in channel.findall("item")
        if (n.findtext("category") or "").strip() == "entertainment"
    ]

    kept: list[ET.Element] = []
    removed_low = 0
    removed_dup = 0

    for node in entertainment:
        if low_value(node):
            channel.remove(node)
            removed_low += 1
            continue

        duplicate_of = next((prior for prior in kept if same_event(prior, node)), None)
        if duplicate_of is not None:
            add_related(duplicate_of, node)
            channel.remove(node)
            removed_dup += 1
            continue

        kept.append(node)

    if len(kept) < MIN_HEALTHY:
        raise SystemExit(
            f"Entertainment rank guard refused thin result: {len(kept)} < {MIN_HEALTHY}"
        )

    ET.indent(tree, space="  ")
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(
        f"Entertainment rank guard: {len(entertainment)} ranked -> {len(kept)} final; "
        f"removed {removed_dup} duplicate event card(s), {removed_low} low-value card(s)."
    )
    for i, node in enumerate(kept[:15], 1):
        print(f"  {i:02d}. {title(node)}")


if __name__ == "__main__":
    main()
