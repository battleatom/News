#!/usr/bin/env python3
"""Recover vetted specialist inventory lost by the generic ownership pass.

The full refinement chain runs enforce_nfl_final.py immediately before the generic
V5 global ownership filter. That specialist guard knows more about NFL headlines
than the generic classifier, so this script can safely recover specialist-approved
NFL records from a pre-global-filter snapshot when the generic pass over-prunes.

Only NFL is recovered here. Recovered stories are revalidated with nfl_relevant(),
deduplicated against the current feed, and capped to the release target. The B2
source ladder/finalizer still ranks and balances the recovered inventory afterward.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from enforce_nfl_final import nfl_relevant

TARGET_NFL = 25


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="Pre-global-filter News snapshot")
    p.add_argument("--target", default="News")
    p.add_argument("--nfl-target", type=int, default=TARGET_NFL)
    args = p.parse_args()

    target_tree = ET.parse(args.target)
    target_channel = target_tree.getroot().find("channel")
    source_tree = ET.parse(args.source)
    source_channel = source_tree.getroot().find("channel")
    if target_channel is None or source_channel is None:
        raise SystemExit("RSS channel missing")

    current = list(target_channel.findall("item"))
    nfl_current = [x for x in current if field(x, "category").lower() == "nfl"]
    existing = {key(x) for x in current}
    need = max(0, args.nfl_target - len(nfl_current))
    recovered = []

    if need:
        for item in source_channel.findall("item"):
            if field(item, "category").lower() != "nfl":
                continue
            if not nfl_relevant(item):
                continue
            k = key(item)
            if k in existing:
                continue
            recovered.append(item)
            existing.add(k)
            if len(recovered) >= need:
                break

    if recovered:
        # Keep the category block coherent. B2 source ladders will perform the final
        # per-publisher ranking/round-robin later in the workflow.
        insertion = None
        for idx, item in enumerate(current):
            if field(item, "category").lower() == "nfl":
                insertion = idx + 1
        if insertion is None:
            insertion = len(current)
        rebuilt = current[:insertion] + recovered + current[insertion:]
        for item in current:
            target_channel.remove(item)
        for item in rebuilt:
            target_channel.append(item)
        target_tree.write(args.target, encoding="utf-8", xml_declaration=True)

    final_count = len(nfl_current) + len(recovered)
    print(f"NFL inventory recovery: {len(nfl_current)} -> {final_count}; recovered {len(recovered)} specialist-approved item(s); target={args.nfl_target}")
    if final_count < min(args.nfl_target, len([x for x in source_channel.findall('item') if field(x, 'category').lower() == 'nfl' and nfl_relevant(x)])):
        raise SystemExit("NFL recovery could not restore available specialist-approved inventory")


if __name__ == "__main__":
    main()
