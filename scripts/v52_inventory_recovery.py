#!/usr/bin/env python3
"""Recover vetted inventory lost by the generic ownership pass.

The full refinement chain snapshots the feed immediately before the generic V5
ownership filter. This script restores only records that still pass specialist
category validation, then leaves final ranking/dedupe/source smoothing to B2.

NFL uses the dedicated nfl_relevant() guard. Presidential recovery is deliberately
strict: the record must pass the presidential tab qualifier and contain an explicit
presidential/White House/Trump anchor in its title or description. This restores
useful depth without reintroducing generic politics or unrelated stories.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from enforce_nfl_final import nfl_relevant
from v5_tab_filters import qualifies

TARGET_NFL = 25
TARGET_PRESIDENTIAL = 58
PRESIDENTIAL_ANCHOR = re.compile(
    r"\b(donald\s+trump|president\s+trump|trump\s+administration|white\s+house|"
    r"oval\s+office|executive\s+order|press\s+secretary|presidential\s+administration)\b",
    re.I,
)


def field(item, name):
    return (item.findtext(name) or "").strip()


def norm_title(value):
    value = re.sub(r"\s+-\s+[^-]{2,50}$", "", (value or "").lower())
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())


def norm_url(value):
    try:
        p = urlsplit(value or "")
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))
    except Exception:
        return value or ""


def key(item):
    url = norm_url(field(item, "link"))
    if url:
        return ("url", url)
    return ("title", norm_title(field(item, "title")), re.sub(r"[^a-z0-9]+", "", field(item, "source").lower()))


def presidential_relevant(item):
    if field(item, "category").lower() != "presidential":
        return False
    try:
        if not qualifies(item, "presidential"):
            return False
    except Exception:
        return False
    text = f"{field(item, 'title')} {field(item, 'description')}"
    return bool(PRESIDENTIAL_ANCHOR.search(text))


def recover_category(current, source_channel, category, target, predicate, existing):
    category_current = [x for x in current if field(x, "category").lower() == category]
    need = max(0, target - len(category_current))
    recovered = []
    if need:
        for item in source_channel.findall("item"):
            if field(item, "category").lower() != category:
                continue
            if not predicate(item):
                continue
            k = key(item)
            if k in existing:
                continue
            recovered.append(item)
            existing.add(k)
            if len(recovered) >= need:
                break
    return category_current, recovered


def insert_after_category(current, recovered, category):
    if not recovered:
        return current
    insertion = None
    for idx, item in enumerate(current):
        if field(item, "category").lower() == category:
            insertion = idx + 1
    if insertion is None:
        insertion = len(current)
    return current[:insertion] + recovered + current[insertion:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="Pre-global-filter News snapshot")
    p.add_argument("--target", default="News")
    p.add_argument("--nfl-target", type=int, default=TARGET_NFL)
    p.add_argument("--presidential-target", type=int, default=TARGET_PRESIDENTIAL)
    args = p.parse_args()

    target_tree = ET.parse(args.target)
    target_channel = target_tree.getroot().find("channel")
    source_tree = ET.parse(args.source)
    source_channel = source_tree.getroot().find("channel")
    if target_channel is None or source_channel is None:
        raise SystemExit("RSS channel missing")

    current = list(target_channel.findall("item"))
    existing = {key(x) for x in current}

    nfl_current, nfl_recovered = recover_category(
        current, source_channel, "nfl", args.nfl_target, nfl_relevant, existing
    )
    current = insert_after_category(current, nfl_recovered, "nfl")

    presidential_current, presidential_recovered = recover_category(
        current,
        source_channel,
        "presidential",
        args.presidential_target,
        presidential_relevant,
        existing,
    )
    current = insert_after_category(current, presidential_recovered, "presidential")

    if nfl_recovered or presidential_recovered:
        for item in list(target_channel.findall("item")):
            target_channel.remove(item)
        for item in current:
            target_channel.append(item)
        target_tree.write(args.target, encoding="utf-8", xml_declaration=True)

    nfl_final = len(nfl_current) + len(nfl_recovered)
    pres_final = len(presidential_current) + len(presidential_recovered)
    print(
        f"NFL inventory recovery: {len(nfl_current)} -> {nfl_final}; recovered {len(nfl_recovered)}; target={args.nfl_target}"
    )
    print(
        f"Presidential inventory recovery: {len(presidential_current)} -> {pres_final}; recovered {len(presidential_recovered)} strictly-qualified item(s); target={args.presidential_target}"
    )

    available_nfl = len([
        x for x in source_channel.findall("item")
        if field(x, "category").lower() == "nfl" and nfl_relevant(x)
    ])
    if nfl_final < min(args.nfl_target, available_nfl):
        raise SystemExit("NFL recovery could not restore available specialist-approved inventory")

    available_pres = len([
        x for x in source_channel.findall("item") if presidential_relevant(x)
    ])
    if pres_final < min(args.presidential_target, available_pres):
        raise SystemExit("Presidential recovery could not restore available strictly-qualified inventory")


if __name__ == "__main__":
    main()
