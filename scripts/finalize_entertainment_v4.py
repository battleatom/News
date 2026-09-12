#!/usr/bin/env python3
"""Finalize verified Entertainment records without recollecting them.

Adds deterministic GUIDs and rebuilds optional red Underreported cross-links against
only the Underreported stories that survived the final verifier.
"""
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

import update_news_v4 as v4

NEWS = Path("News")


def value(node: ET.Element, tag: str) -> str:
    return (node.findtext(tag) or "").strip()


def as_item(node: ET.Element) -> dict:
    return {
        "title": value(node, "title"),
        "description": value(node, "description"),
        "link": value(node, "link"),
        "source": value(node, "source"),
        "category": value(node, "category"),
    }


def ensure_guid(node: ET.Element) -> None:
    link = value(node, "link")
    category = value(node, "category")
    expected = hashlib.sha1(f"{link}|{category}".encode("utf-8")).hexdigest()
    guid = node.find("guid")
    if guid is None:
        guid = ET.SubElement(node, "guid")
    guid.set("isPermaLink", "false")
    guid.text = expected


def rebuild_underreported_links(ent_node: ET.Element, ent: dict, underreported: list[tuple[ET.Element, dict]]) -> int:
    old = ent_node.find("underreportedLinks")
    if old is not None:
        ent_node.remove(old)

    matches = []
    for _, under in underreported:
        try:
            related = v4._related_to_underreported(ent, under)
        except Exception:
            related = False
        if not related:
            continue
        matches.append(under)
        if len(matches) >= 2:
            break

    if not matches:
        return 0

    parent = ET.SubElement(ent_node, "underreportedLinks")
    for match in matches:
        article = ET.SubElement(parent, "article")
        for tag in ("title", "link", "source"):
            child = ET.SubElement(article, tag)
            child.text = match.get(tag, "")
    return len(matches)


def main() -> None:
    if not NEWS.exists():
        raise SystemExit("News feed not found")
    tree = ET.parse(NEWS)
    root = tree.getroot()
    items = root.findall(".//item")
    entertainment_nodes = [n for n in items if value(n, "category") == "entertainment"]
    underreported = [(n, as_item(n)) for n in items if value(n, "category") == "underreported"]

    link_count = 0
    for node in entertainment_nodes:
        ensure_guid(node)
        link_count += rebuild_underreported_links(node, as_item(node), underreported)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(
        f"Finalized {len(entertainment_nodes)} Entertainment record(s); "
        f"attached {link_count} verified Underreported cross-link(s)."
    )


if __name__ == "__main__":
    main()
