#!/usr/bin/env python3
"""Test-branch-only source patcher for the 50 active + 25 reserve inventory experiment.

This intentionally patches the checked-out workflow workspace at test time instead of
changing production collector behavior on main. Box Office and fixed X are excluded.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, replacements):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    original = text
    for old, new, required in replacements:
        if old not in text:
            if required:
                raise SystemExit(f"Deep inventory patch anchor missing in {path}: {old!r}")
            continue
        text = text.replace(old, new)
    if text == original:
        raise SystemExit(f"Deep inventory patch made no changes to {path}")
    p.write_text(text, encoding="utf-8")
    print(f"Patched {path}")


# Generic collector: collect deeper than the final 75 so final semantic filtering has room.
patch("scripts/update_news_normalized.py", [
    ('"world": (30, 35, 40), "us": (30, 35, 40), "presidential": (30, 35, 40),',
     '"world": (75, 100, 120), "us": (75, 100, 120), "presidential": (75, 100, 120),', True),
    ('"federal": (30, 35, 40), "nm": (30, 35, 40), "region": (30, 35, 80),',
     '"federal": (75, 100, 120), "nm": (50, 75, 90), "region": (30, 35, 80),', True),
    ('"nfl": (30, 35, 40), "technology": (30, 35, 40), "gaming": (30, 35, 40),',
     '"nfl": (75, 100, 120), "technology": (75, 100, 120), "gaming": (75, 100, 120),', True),
    ('"military": (30, 35, 40),', '"military": (50, 75, 90),', True),
    ('core.MAX_AGE_HOURS = 96', 'core.MAX_AGE_HOURS = 168', True),
    ('f"{query} when:4d"', 'f"{query} when:7d"', True),
])

# Specialist pools: retain more already-vetted stories before final ownership/filtering.
patch("scripts/refine_tech_gaming.py", [
    ('MAX_TECH = 25', 'MAX_TECH = 90', True),
    ('MAX_GAMING = 20', 'MAX_GAMING = 90', True),
    ('MAX_US = 20', 'MAX_US = 90', True),
    ("fetch_google(TECH_QUERIES, 'technology', 2)", "fetch_google(TECH_QUERIES, 'technology', 7)", True),
    ("fetch_google(GAMING_QUERIES, 'gaming', 2)", "fetch_google(GAMING_QUERIES, 'gaming', 7)", True),
    ("fetch_google(US_QUERIES, 'us', 2)", "fetch_google(US_QUERIES, 'us', 7)", True),
])

patch("scripts/refine_entertainment.py", [
    ('TARGET = 30', 'TARGET = 90', True),
    ('MIN_HEALTHY = 15', 'MIN_HEALTHY = 50', True),
    ('FRESH_HOURS = 48', 'FRESH_HOURS = 72', True),
    ('LOOKBACK_HOURS = 96', 'LOOKBACK_HOURS = 168', True),
])

patch("scripts/underreported_priority.py", [
    ('MAX_ITEMS = 30', 'MAX_ITEMS = 75', True),
])

# NFL is year-round: preserve the current queries and add offseason/draft/camp discovery.
patch("scripts/update_news.py", [
    ('    "nfl": [\n        "NFL news",\n        "NFL injuries trades free agency",\n        "NFL scores results",\n    ],',
     '    "nfl": [\n        "NFL news",\n        "NFL injuries trades free agency",\n        "NFL scores results",\n        "NFL offseason news trades contracts roster",\n        "NFL draft combine pro day",\n        "NFL OTAs minicamp training camp roster cuts",\n        "NFL coaching front office rule changes suspensions",\n    ],', True),
])

# UI: show 50 immediately; keep the next 25 as the natural reserve/load-more tranche.
patch("scripts/patch_load_more.py", [
    ('const STORIES_PER_PAGE = 10;', 'const STORIES_PER_PAGE = 50;\nconst RESERVE_PAGE = 25;', True),
    ('(loadCounts[active]||STORIES_PER_PAGE)+STORIES_PER_PAGE', '(loadCounts[active]||STORIES_PER_PAGE)+RESERVE_PAGE', True),
])

patch("assets/card-feedback.js", [
    ('const current=Number(counts[key]||10);', 'const current=Number(counts[key]||50);', True),
    ('counts[key]=Number.isFinite(current)?current+1:11;', 'counts[key]=Number.isFinite(current)?current+1:51;', True),
])

print("Deep inventory test policy enabled: 50 active + 25 reserve; X fixed; Legislation unchanged at 30; Box Office untouched.")
