#!/usr/bin/env python3
"""Shadow-mode category/source classifier for live News feed testing.

This intentionally does NOT modify production News. It reads the generated RSS,
validates source trust using the collector's existing trust function, scores each
article against supported categories, and writes:
  - classifier-report.json (decisions + confidence)
  - News.classified-preview (rerouted/rejected preview feed)

The goal is to measure classifier behavior on real live pulls before integration.
"""

from __future__ import annotations

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS_PATH = ROOT / "News"
REPORT_PATH = ROOT / "classifier-report.json"
PREVIEW_PATH = ROOT / "News.classified-preview"

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from update_news import source_is_trusted  # reuse production allowlist logic
except Exception as exc:  # fail closed if trust policy cannot be loaded
    raise SystemExit(f"Could not load production source trust policy: {exc}")

SUPPORTED = [
    "world", "us", "presidential", "federal", "legislation", "nm", "local",
    "region", "nfl", "technology", "gaming", "military", "underreported",
]

# Weighted semantic vocabulary. Phrase matches count more than single words.
SIGNALS = {
    "world": {
        "international": 3, "foreign": 2, "diplomatic": 3, "diplomacy": 3,
        "sanctions": 3, "nato": 4, "united nations": 4, "ukraine": 4,
        "russia": 4, "china": 3, "iran": 4, "israel": 4, "gaza": 4,
        "europe": 2, "asia": 2, "africa": 2, "middle east": 4,
    },
    "us": {
        "united states": 4, "u.s.": 4, "american": 2, "nationwide": 2,
        "state officials": 2, "governor": 2, "state law": 2,
    },
    "presidential": {
        "president trump": 6, "donald trump": 6, "white house": 5,
        "president": 2, "executive order": 5, "presidential": 5,
        "administration": 2, "cabinet": 3,
    },
    "federal": {
        "congress": 5, "senate": 4, "house of representatives": 5,
        "supreme court": 6, "scotus": 6, "department of justice": 5,
        "doj": 4, "fbi": 4, "dhs": 4, "federal": 3, "treasury": 3,
        "epa": 3, "sec": 3, "fcc": 3, "irs": 3,
    },
    "legislation": {
        "bill": 4, "legislation": 6, "signed into law": 7, "lawmakers": 3,
        "statute": 5, "regulation": 4, "rulemaking": 5, "ordinance": 6,
        "executive order": 4, "final rule": 6,
    },
    "nm": {
        "new mexico": 7, "santa fe": 3, "albuquerque": 3, "nm legislature": 7,
        "new mexico governor": 6,
    },
    "local": {
        "farmington": 8, "san juan county": 8, "aztec": 7, "bloomfield": 7,
        "kirtland": 6, "shiprock": 7, "four corners": 8, "durango": 6,
        "la plata county": 7, "cortez": 6, "montezuma county": 7,
        "navajo nation": 6, "gallup": 5,
    },
    "region": {
        "arizona": 3, "colorado": 3, "utah": 3, "nevada": 3, "wyoming": 3,
        "montana": 3, "idaho": 3, "southwest": 4, "rocky mountain": 4,
        "pacific northwest": 4,
    },
    "nfl": {
        "nfl": 8, "national football league": 8, "touchdown": 4,
        "quarterback": 4, "super bowl": 7, "football": 2, "roster": 3,
        "free agency": 4, "training camp": 4,
    },
    "technology": {
        "artificial intelligence": 7, " ai ": 4, "openai": 7, "chatgpt": 7,
        "cybersecurity": 7, "data breach": 7, "cyberattack": 7, "software": 4,
        "semiconductor": 6, "chip": 3, "nvidia": 6, "amd": 5, "intel": 5,
        "microsoft": 4, "google": 3, "apple": 3, "cloud computing": 6,
        "robotics": 5, "quantum computing": 7, "tech company": 4,
    },
    "gaming": {
        "video game": 7, "gaming": 7, "playstation": 7, "xbox": 7,
        "nintendo": 7, "steam": 5, "game studio": 6, "console": 5,
        "pc gaming": 7, "esports": 6,
    },
    "military": {
        "pentagon": 7, "military": 5, "troops": 5, "armed forces": 6,
        "air force": 5, "army": 4, "navy": 4, "marines": 5, "missile": 4,
        "airstrike": 5, "defense department": 7, "war": 3,
    },
    "underreported": {
        "investigation": 3, "public records": 4, "accountability": 4,
        "infrastructure": 2, "water": 2, "environmental": 2, "rural": 2,
        "tribal": 3, "public health": 3,
    },
}

NEGATIVE = {
    "technology": {"touchdown": -6, "nfl": -8, "recipe": -5, "celebrity": -3},
    "gaming": {"casino": -7, "gambling": -7, "sportsbook": -7},
    "nfl": {"soccer": -5, "college football": -4, "high school football": -6},
    "world": {"local weather": -4},
}

# More-specific sections win ties against broad sections.
SPECIFICITY = {
    "local": 9, "nm": 8, "presidential": 8, "legislation": 8, "nfl": 8,
    "gaming": 8, "technology": 7, "military": 7, "federal": 7, "region": 6,
    "world": 4, "us": 4, "underreported": 2,
}

# Sections that are editorial/ranking surfaces rather than mutually exclusive topics.
NON_ROUTABLE_INPUT = {"top"}


def text_of(item: ET.Element) -> str:
    parts = [item.findtext("title", ""), item.findtext("description", "")]
    return " " + re.sub(r"\s+", " ", " ".join(parts)).lower().strip() + " "


def phrase_present(text: str, phrase: str) -> bool:
    p = phrase.lower()
    if p.startswith(" ") or p.endswith(" "):
        return p in text
    if " " in p or "." in p:
        return p in text
    return re.search(rf"\b{re.escape(p)}\b", text) is not None


def score_categories(text: str, current: str) -> dict[str, float]:
    scores = {cat: 0.0 for cat in SUPPORTED}
    evidence = defaultdict(list)
    for cat, terms in SIGNALS.items():
        for term, weight in terms.items():
            if phrase_present(text, term):
                scores[cat] += weight
                evidence[cat].append(term.strip())
    for cat, terms in NEGATIVE.items():
        for term, weight in terms.items():
            if phrase_present(text, term):
                scores[cat] += weight
                evidence[cat].append(f"!{term}")

    # Provider/collector category is a weak prior, not an authority.
    if current in scores:
        scores[current] += 2.0
        evidence[current].append("existing-category-prior")

    # Geographic hierarchy: local should outrank state/region; NM outranks generic region.
    if scores["local"] >= 7:
        scores["nm"] -= 2
        scores["region"] -= 3
    elif scores["nm"] >= 6:
        scores["region"] -= 2

    return scores, evidence


def confidence(scores: dict[str, float], winner: str) -> float:
    ordered = sorted(scores.values(), reverse=True)
    top = ordered[0] if ordered else 0.0
    second = ordered[1] if len(ordered) > 1 else 0.0
    if top <= 0:
        return 0.0
    # Confidence rewards absolute evidence and separation from runner-up.
    strength = 1.0 - math.exp(-top / 8.0)
    separation = max(0.0, min(1.0, (top - second) / max(4.0, top)))
    return round(min(0.99, 0.62 * strength + 0.38 * separation), 3)


def classify(item: ET.Element) -> dict:
    source = (item.findtext("source") or "").strip()
    current = (item.findtext("category") or "").strip().lower()
    title = (item.findtext("title") or "").strip()

    if not source or not source_is_trusted(source):
        return {
            "title": title, "source": source, "current": current,
            "action": "reject", "reason": "unapproved-source", "category": None,
            "confidence": 1.0, "scores": {}, "evidence": [],
        }

    if current in NON_ROUTABLE_INPUT:
        return {
            "title": title, "source": source, "current": current,
            "action": "keep", "reason": "ranking-surface-not-rerouted", "category": current,
            "confidence": 1.0, "scores": {}, "evidence": [],
        }

    text = text_of(item)
    scores, evidence = score_categories(text, current)
    ranked = sorted(scores, key=lambda c: (scores[c], SPECIFICITY.get(c, 0)), reverse=True)
    winner = ranked[0]
    top_score = scores[winner]
    conf = confidence(scores, winner)

    # Fail conservatively: weak semantic evidence does not get auto-rerouted.
    if top_score < 4.0:
        return {
            "title": title, "source": source, "current": current,
            "action": "review", "reason": "insufficient-semantic-evidence",
            "category": current or None, "confidence": conf,
            "scores": {k: round(v, 2) for k, v in scores.items() if v},
            "evidence": evidence.get(winner, [])[:8],
        }

    if winner == current:
        action, reason = "keep", "category-confirmed"
    elif conf >= 0.72:
        action, reason = "reroute", f"semantic-match:{winner}"
    else:
        action, reason = "review", f"ambiguous:{winner}"

    return {
        "title": title, "source": source, "current": current,
        "action": action, "reason": reason, "category": winner,
        "confidence": conf,
        "scores": {k: round(v, 2) for k, v in scores.items() if v},
        "evidence": evidence.get(winner, [])[:8],
    }


def main() -> None:
    if not NEWS_PATH.exists():
        raise SystemExit("News feed not found. Run scripts/update_news.py first.")

    tree = ET.parse(NEWS_PATH)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")

    decisions = []
    counts = Counter()
    transitions = Counter()

    preview_root = deepcopy(root)
    preview_channel = preview_root.find("channel")
    preview_items = list(preview_channel.findall("item")) if preview_channel is not None else []

    for original, preview in zip(channel.findall("item"), preview_items):
        d = classify(original)
        decisions.append(d)
        counts[d["action"]] += 1
        if d["action"] == "reroute":
            transitions[f"{d['current']}->{d['category']}"] += 1
            cat = preview.find("category")
            if cat is None:
                cat = ET.SubElement(preview, "category")
            cat.text = d["category"]
            ET.SubElement(preview, "classifierConfidence").text = str(d["confidence"])
            ET.SubElement(preview, "classifierOriginalCategory").text = d["current"]
        elif d["action"] == "reject":
            preview_channel.remove(preview)
        elif d["action"] == "review":
            ET.SubElement(preview, "classifierReview").text = "true"
            ET.SubElement(preview, "classifierConfidence").text = str(d["confidence"])

    total = len(decisions)
    report = {
        "mode": "shadow-live-test",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "input": str(NEWS_PATH.name),
        "totalArticles": total,
        "summary": dict(counts),
        "reroutes": dict(transitions.most_common()),
        "policy": {
            "sourceValidation": "production update_news.source_is_trusted",
            "rerouteThreshold": 0.72,
            "minimumSemanticScore": 4.0,
            "productionFeedModified": False,
        },
        "decisions": decisions,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ET.ElementTree(preview_root).write(PREVIEW_PATH, encoding="utf-8", xml_declaration=True)

    print(f"Classifier shadow test: {total} articles")
    print("Actions:", dict(counts))
    if transitions:
        print("Top reroutes:", dict(transitions.most_common(12)))
    print(f"Report: {REPORT_PATH.name}")
    print(f"Preview: {PREVIEW_PATH.name}")


if __name__ == "__main__":
    main()
