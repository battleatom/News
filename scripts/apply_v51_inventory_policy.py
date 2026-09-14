#!/usr/bin/env python3
"""Apply the tested V5.1 deep-inventory policy to production source files.

This is intentionally idempotent. The V5.1 preview used the same replacements in an
isolated Actions workspace; this promotion script makes those tested settings permanent
on main. Box Office and fixed X behavior are not modified.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, replacements):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    changed = False
    for old, new in replacements:
        if new in text:
            continue
        if old not in text:
            raise SystemExit(f"V5.1 promotion anchor missing in {path}: {old!r}")
        text = text.replace(old, new)
        changed = True
    if changed:
        p.write_text(text, encoding="utf-8")
        print(f"V5.1 patched {path}")
    else:
        print(f"V5.1 already applied to {path}")


patch("scripts/update_news_normalized.py", [
    ('"world": (30, 35, 40), "us": (30, 35, 40), "presidential": (30, 35, 40),',
     '"world": (75, 100, 120), "us": (75, 100, 120), "presidential": (75, 100, 120),'),
    ('"federal": (30, 35, 40), "nm": (30, 35, 40), "region": (30, 35, 80),',
     '"federal": (75, 100, 120), "nm": (50, 75, 90), "region": (30, 35, 80),'),
    ('"nfl": (30, 35, 40), "technology": (30, 35, 40), "gaming": (30, 35, 40),',
     '"nfl": (75, 100, 120), "technology": (75, 100, 120), "gaming": (75, 100, 120),'),
    ('"military": (30, 35, 40),', '"military": (50, 75, 90),'),
    ('core.MAX_AGE_HOURS = 96', 'core.MAX_AGE_HOURS = 168'),
    ('f"{query} when:4d"', 'f"{query} when:7d"'),
])

patch("scripts/refine_tech_gaming.py", [
    ('MAX_TECH = 25', 'MAX_TECH = 90'),
    ('MAX_GAMING = 20', 'MAX_GAMING = 90'),
    ('MAX_US = 20', 'MAX_US = 90'),
    ("fetch_google(TECH_QUERIES, 'technology', 2)", "fetch_google(TECH_QUERIES, 'technology', 7)"),
    ("fetch_google(GAMING_QUERIES, 'gaming', 2)", "fetch_google(GAMING_QUERIES, 'gaming', 7)"),
    ("fetch_google(US_QUERIES, 'us', 2)", "fetch_google(US_QUERIES, 'us', 7)"),
])

patch("scripts/refine_entertainment.py", [
    ('TARGET = 30', 'TARGET = 90'),
    ('MIN_HEALTHY = 15', 'MIN_HEALTHY = 50'),
    ('FRESH_HOURS = 48', 'FRESH_HOURS = 72'),
    ('LOOKBACK_HOURS = 96', 'LOOKBACK_HOURS = 168'),
])

patch("scripts/underreported_priority.py", [
    ('MAX_ITEMS = 30', 'MAX_ITEMS = 75'),
])

patch("scripts/update_news.py", [
    ('    "nfl": [\n        "NFL news",\n        "NFL injuries trades free agency",\n        "NFL scores results",\n    ],',
     '    "nfl": [\n        "NFL news",\n        "NFL injuries trades free agency",\n        "NFL scores results",\n        "NFL offseason news trades contracts roster",\n        "NFL draft combine pro day",\n        "NFL OTAs minicamp training camp roster cuts",\n        "NFL coaching front office rule changes suspensions",\n    ],'),
])

patch("scripts/patch_load_more.py", [
    ('const STORIES_PER_PAGE = 10;', 'const STORIES_PER_PAGE = 50;\nconst RESERVE_PAGE = 25;'),
    ('(loadCounts[active]||STORIES_PER_PAGE)+STORIES_PER_PAGE', '(loadCounts[active]||STORIES_PER_PAGE)+RESERVE_PAGE'),
])

patch("assets/card-feedback.js", [
    ('const current=Number(counts[key]||10);', 'const current=Number(counts[key]||50);'),
    ('counts[key]=Number.isFinite(current)?current+1:11;', 'counts[key]=Number.isFinite(current)?current+1:51;'),
])

print("V5.1 production policy ready: 50 active + 25 reserve where inventory supports it; X fixed; Box Office untouched.")
