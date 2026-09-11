#!/usr/bin/env python3
"""Final feed verification gate.

Runs after collection/enrichment and before content briefs/site generation.
It owns the final source/category/deduplication decision for each article:
  * reject unapproved sources
  * apply high-confidence category reroutes
  * collapse syndicated copies and same-event coverage within each tab
  * preserve removed coverage as supporting links on the strongest card
  * emit a machine-readable decision report

The same real-world event may legitimately appear in more than one tab. Clustering
therefore remains per-tab, after category routing has been applied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "News"
REPORT = ROOT / "verification-report.json"
sys.path.insert(0, str(ROOT / "scripts"))

import dedupe_news_legacy as legacy
from classify_live_feed import SPECIFICITY, classify

EDITORIAL_SURFACES = {"top", "underreported", "x", "boxoffice", "legislation"}
HIGH_CONFIDENCE_REROUTE = 0.80
SPECIFIC_REROUTE = 0.72

EVENT_GROUPS = {
    "payments": {"payment", "payments", "check", "checks", "rebate", "rebates", "dividend", "dividends", "stimulus", "refund", "refunds", "bonus", "bonuses", "payout", "payouts", "cash"},
    "elections": {"election", "elections", "midterm", "midterms", "vote", "votes", "voting", "ballot", "ballots", "campaign", "campaigns"},
    "immigration": {"immigration", "immigrant", "immigrants", "migrant", "migrants", "border", "deportation", "deportations", "asylum", "visa", "visas"},
    "courts": {"court", "courts", "judge", "judges", "ruling", "rulings", "lawsuit", "lawsuits", "supreme", "appeal", "appeals", "injunction"},
    "legislation": {"bill", "bills", "law", "laws", "legislation", "ordinance", "regulation", "regulations", "rule", "rules", "executive", "order"},
    "military": {"war", "airstrike", "airstrikes", "missile", "missiles", "strike", "strikes", "troops", "invasion", "ceasefire", "battle", "attack", "attacks", "raid", "raids"},
    "crime": {"shooting", "shootings", "murder", "murders", "homicide", "arrest", "arrests", "charged", "charges", "indictment", "stabbing"},
    "disaster": {"hurricane", "tornado", "tornadoes", "wildfire", "wildfires", "flood", "floods", "earthquake", "storm", "storms", "disaster", "evacuation"},
    "economy": {"economy", "economic", "inflation", "jobs", "unemployment", "recession", "prices", "wages", "tariff", "tariffs", "market", "markets", "trade"},
    "technology": {"ai", "software", "cybersecurity", "breach", "hack", "hacked", "outage", "chip", "chips", "semiconductor", "launch", "update", "vulnerability"},
    "gaming": {"gaming", "game", "games", "playstation", "xbox", "nintendo", "steam", "console", "studio", "release", "trailer", "showcase"},
    "sports": {"nfl", "football", "touchdown", "quarterback", "roster", "trade", "injury", "playoffs", "super", "bowl", "game", "score"},
    "health": {"health", "healthcare", "medicaid", "medicare", "insurance", "hospital", "hospitals", "recall", "outbreak"},
    "education": {"school", "schools", "college", "colleges", "university", "universities", "student", "students", "education"},
}

GENERIC = set().union(*EVENT_GROUPS.values()) | {
    "president", "presidential", "white", "house", "administration", "government",
    "federal", "official", "officials", "american", "americans", "united", "states",
    "news", "breaking", "today", "latest", "new", "plan", "plans", "proposal",
    "proposals", "proposed", "announce", "announces", "announced", "says", "said",
    "could", "would", "may", "might", "people", "week", "weeks", "season", "live",
    "results", "result", "schedule", "scores",
}
SOURCE_TIERS = {
    "reuters": 10, "associated press": 10, "ap news": 10, "bbc": 9,
    "npr": 9, "cbs news": 8, "nbc news": 8, "abc news": 8, "cnn": 8,
    "the new york times": 8, "the washington post": 8, "usa today": 7,
    "politico": 7, "the hill": 7, "ars technica": 8, "the verge": 8,
    "techcrunch": 7, "ign": 7, "gamespot": 7, "nfl.com": 8, "espn": 8,
}
HIGH_COLLISION_CATEGORIES = {"region", "local", "nm", "nfl", "technology", "gaming"}
CATEGORY_ANCHOR_MIN = {
    "technology": 4, "gaming": 4, "nfl": 4, "world": 3, "military": 3,
    "federal": 3, "presidential": 3, "legislation": 3, "us": 3, "nm": 3,
    "local": 3, "region": 2, "top": 3, "underreported": 3,
}


def clean(value: str | None) -> str:
    return legacy.clean(value or "").strip()


def category(item: ET.Element) -> str:
    return clean(item.findtext("category")).lower()


def title(item: ET.Element) -> str:
    return legacy.title_without_source(item)


def full_text(item: ET.Element) -> str:
    return f"{title(item)} {clean(item.findtext('description'))}".strip()


def normalized_tokens(item: ET.Element) -> set[str]:
    words = re.findall(r"[a-z0-9]+", full_text(item).lower())
    return {w for w in words if len(w) >= 3 and w not in legacy.STOP_WORDS}


def title_tokens(item: ET.Element) -> set[str]:
    words = re.findall(r"[a-z0-9]+", title(item).lower())
    return {w for w in words if len(w) >= 3 and w not in legacy.STOP_WORDS}


def title_specific_tokens(item: ET.Element) -> set[str]:
    return title_tokens(item) - GENERIC


def specific_tokens(item: ET.Element) -> set[str]:
    return normalized_tokens(item) - GENERIC


def event_groups(item: ET.Element) -> set[str]:
    toks = normalized_tokens(item)
    return {name for name, words in EVENT_GROUPS.items() if toks & words}


def amount_keys(item: ET.Element) -> set[str]:
    text = full_text(item)
    keys: set[str] = set()
    for raw in re.findall(r"\$\s*([0-9][0-9,]*(?:\.\d+)?)", text):
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        keys.add(f"usd:{value:g}")
    for raw in re.findall(r"\b([1-9][0-9]{3,}|[1-9][0-9]{0,2}(?:,[0-9]{3})+)\b", text):
        try:
            value = int(raw.replace(",", ""))
        except ValueError:
            continue
        if 1900 <= value <= 2100:
            continue
        if value >= 1000:
            keys.add(f"num:{value}")
    return keys


def entity_keys(item: ET.Element) -> set[str]:
    raw = title(item)
    chunks = re.findall(r"\b(?:[A-Z][a-z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]+|[A-Z]{2,})){0,3}\b", raw)
    noise = {"the", "new", "united states", "white house", "president", "news", "breaking", "today"}
    out = set()
    for chunk in chunks:
        key = re.sub(r"\s+", " ", chunk.lower()).strip()
        if key not in noise and len(key) >= 3:
            out.add(key)
    return out


def actor_keys(item: ET.Element) -> set[str]:
    """Generic proper-name anchors used only with another event fingerprint.

    Single surnames and organization names are intentionally retained here. They are
    never sufficient by themselves to cluster stories; an amount/event group or strong
    lexical overlap must also match.
    """
    raw = f"{title(item)} {clean(item.findtext('description'))[:500]}"
    words = re.findall(r"\b[A-Z][A-Za-z'’-]{2,}\b", raw)
    noise = {"The", "This", "That", "News", "Breaking", "Update", "Exclusive", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    return {w.lower() for w in words if w not in noise}


def near_exact_title(a: ET.Element, b: ET.Element) -> bool:
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return False
    shared = len(ta & tb)
    smaller = min(len(ta), len(tb))
    return smaller >= 5 and shared >= 5 and shared / smaller >= 0.86


def syndicated_copy(a: ET.Element, b: ET.Element) -> bool:
    """Detect wire/syndicated copies even when the republisher changes the suffix."""
    ta, tb = title_tokens(a), title_tokens(b)
    ba, bb = normalized_tokens(a), normalized_tokens(b)
    if not ta or not tb or not ba or not bb:
        return False
    title_overlap = len(ta & tb) / max(1, min(len(ta), len(tb)))
    body_overlap = len(ba & bb) / max(1, min(len(ba), len(bb)))
    return (min(len(ta), len(tb)) >= 5 and title_overlap >= 0.82) or (
        min(len(ba), len(bb)) >= 10 and body_overlap >= 0.84 and title_overlap >= 0.58
    )


def same_event(a: ET.Element, b: ET.Element) -> bool:
    if category(a) != category(b):
        return False
    link_a = clean(a.findtext("link")).lower()
    link_b = clean(b.findtext("link")).lower()
    if link_a and link_a == link_b:
        return True
    if not legacy.looks_english(a) or not legacy.looks_english(b):
        return False
    cat = category(a)
    if syndicated_copy(a, b) or near_exact_title(a, b):
        return True
    if cat not in HIGH_COLLISION_CATEGORIES and legacy.same_story(a, b):
        return True

    ga, gb = event_groups(a), event_groups(b)
    shared_groups = ga & gb
    if not shared_groups:
        return False
    amounts = amount_keys(a) & amount_keys(b)
    entities = entity_keys(a) & entity_keys(b)
    actors = actor_keys(a) & actor_keys(b)
    shared = specific_tokens(a) & specific_tokens(b)
    title_shared = title_specific_tokens(a) & title_specific_tokens(b)
    minimum = CATEGORY_ANCHOR_MIN.get(cat, 3)

    # Amount + actor/entity + matching event type is a strong generic fingerprint.
    if amounts and (entities or actors):
        return True
    if amounts and len(shared) >= 2:
        return True
    if entities and len(shared) >= minimum:
        if cat not in HIGH_COLLISION_CATEGORIES or len(title_shared) >= 2:
            return True
    if actors and len(title_shared) >= 2 and len(shared) >= minimum:
        return True

    ta, tb = specific_tokens(a), specific_tokens(b)
    if ta and tb:
        overlap = len(ta & tb) / max(1, min(len(ta), len(tb)))
        threshold = 0.80 if cat in HIGH_COLLISION_CATEGORIES else 0.70
        required = max(4, minimum)
        if len(ta & tb) >= required and overlap >= threshold:
            if cat not in HIGH_COLLISION_CATEGORIES or len(title_shared) >= 3:
                return True
    return False


def parsed_time(item: ET.Element) -> float:
    try:
        dt = parsedate_to_datetime(clean(item.findtext("pubDate")))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def representative_score(item: ET.Element) -> tuple:
    source = clean(item.findtext("source")).lower()
    source_score = max((score for key, score in SOURCE_TIERS.items() if key in source), default=5)
    desc_len = min(len(clean(item.findtext("description"))), 1400)
    title_len = len(title(item))
    return (source_score, parsed_time(item), desc_len, min(title_len, 160))


def event_id(items: list[ET.Element]) -> str:
    anchors = set()
    for item in items:
        anchors |= amount_keys(item)
        anchors |= event_groups(item)
        anchors |= set(sorted(entity_keys(item))[:3])
        anchors |= set(sorted(actor_keys(item))[:3])
        anchors |= set(sorted(specific_tokens(item))[:5])
    payload = "|".join(sorted(anchors)) or "|".join(sorted(title(i).lower() for i in items))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def set_category(item: ET.Element, value: str) -> None:
    node = item.find("category")
    if node is None:
        node = ET.SubElement(item, "category")
    node.text = value


def should_reroute(current: str, decision: dict) -> bool:
    if current in EDITORIAL_SURFACES or decision.get("action") != "reroute":
        return False
    winner = decision.get("category") or ""
    conf = float(decision.get("confidence") or 0)
    if conf >= HIGH_CONFIDENCE_REROUTE:
        return True
    # A clearly more-specific destination (e.g. broad US -> federal/presidential)
    # can move at the classifier's normal confidence threshold.
    return conf >= SPECIFIC_REROUTE and SPECIFICITY.get(winner, 0) >= SPECIFICITY.get(current, 0) + 2


def related_key(node: ET.Element) -> str:
    return (clean(node.findtext("link")) or clean(node.findtext("title"))).lower()


def attach_related(primary: ET.Element, other: ET.Element) -> bool:
    rel = primary.find("relatedArticles")
    if rel is None:
        rel = ET.SubElement(primary, "relatedArticles")
    existing = {related_key(x) for x in rel.findall("article")}
    key = related_key(other)
    if not key or key in existing:
        return False
    ar = ET.SubElement(rel, "article")
    for tag in ("title", "link", "source", "pubDate"):
        value = clean(other.findtext(tag))
        if value:
            ET.SubElement(ar, tag).text = value
    return True


def cluster_indices(items: list[ET.Element]) -> list[list[int]]:
    parent = list(range(len(items)))
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    by_category: dict[str, list[int]] = defaultdict(list)
    for i, item in enumerate(items):
        by_category[category(item)].append(i)
    for indices in by_category.values():
        for pos, i in enumerate(indices):
            for j in indices[pos + 1:]:
                if same_event(items[i], items[j]):
                    union(i, j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)
    return list(groups.values())


def residual_duplicate_pairs(items: list[ET.Element]) -> list[dict]:
    pairs = []
    by_category: dict[str, list[ET.Element]] = defaultdict(list)
    for item in items:
        by_category[category(item)].append(item)
    for cat, group in by_category.items():
        for pos, a in enumerate(group):
            for b in group[pos + 1:]:
                if syndicated_copy(a, b) or near_exact_title(a, b):
                    pairs.append({"category": cat, "a": title(a), "b": title(b)})
    return pairs


def run(feed: Path, apply: bool) -> dict:
    tree = ET.parse(feed)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("Invalid RSS: missing channel")
    original_items = list(channel.findall("item"))
    decisions = []
    rejected: set[int] = set()

    # Route first. Clustering happens only after all high-confidence routes settle,
    # preventing duplicates that entered through different source categories.
    for i, item in enumerate(original_items):
        d = classify(item)
        d["index"] = i
        decisions.append(d)
        if d["action"] == "reject":
            rejected.add(i)
            continue
        current = category(item)
        if should_reroute(current, d):
            set_category(item, d["category"])
            d["applied"] = True
        else:
            d["applied"] = False

    candidate_indices = [i for i in range(len(original_items)) if i not in rejected]
    candidates = [original_items[i] for i in candidate_indices]
    clusters = cluster_indices(candidates)
    removed_event: set[int] = set()
    cluster_report = []
    attached_count = 0
    for cluster in clusters:
        if len(cluster) <= 1:
            continue
        members = [candidates[x] for x in cluster]
        best_local = max(cluster, key=lambda x: representative_score(candidates[x]))
        best_item = candidates[best_local]
        eid = event_id(members)
        removed_titles = []
        for local_idx in cluster:
            if local_idx == best_local:
                continue
            global_idx = candidate_indices[local_idx]
            other = original_items[global_idx]
            if attach_related(best_item, other):
                attached_count += 1
            removed_event.add(global_idx)
            removed_titles.append(title(other))
        cluster_report.append({
            "eventId": eid, "category": category(best_item), "kept": title(best_item),
            "keptSource": clean(best_item.findtext("source")), "removed": removed_titles,
            "size": len(cluster),
        })

    final_items = [item for i, item in enumerate(original_items)
                   if i not in rejected and i not in removed_event and legacy.looks_english(item)]
    residual = residual_duplicate_pairs(final_items)

    if apply:
        for item in list(channel.findall("item")):
            channel.remove(item)
        for item in final_items:
            channel.append(item)
        tree.write(feed, encoding="utf-8", xml_declaration=True)

    action_counts = Counter(d["action"] for d in decisions)
    report = {
        "mode": "apply" if apply else "dry-run",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "inputArticles": len(original_items), "outputArticles": len(final_items),
        "classifierActions": dict(action_counts), "rejectedSources": len(rejected),
        "removedEventDuplicates": len(removed_event), "supportingLinksAttached": attached_count,
        "residualStrongDuplicatePairs": residual, "clusters": cluster_report,
        "decisions": decisions,
        "policy": {
            "rerouteThreshold": HIGH_CONFIDENCE_REROUTE,
            "specificDestinationThreshold": SPECIFIC_REROUTE,
            "eventClustering": "route-first-connected-components-per-tab-with-syndication-detection",
            "representativeSelection": "source-authority, recency, completeness, title-clarity",
            "removedCoveragePolicy": "attach-as-supporting-link",
            "crossTabPolicy": "same event may appear once in each genuinely relevant tab",
            "yearsExcludedFromNumericFingerprint": True,
            "highCollisionCategories": sorted(HIGH_COLLISION_CATEGORIES),
        },
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Verification gate: {len(original_items)} -> {len(final_items)} articles")
    print(f"Rejected sources: {len(rejected)}")
    print(f"Event duplicates removed: {len(removed_event)} across {len(cluster_report)} clusters; {attached_count} supporting links attached")
    print(f"Residual strong duplicate pairs: {len(residual)}")
    print("Classifier actions:", dict(action_counts))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write verified result back to News")
    parser.add_argument("--feed", default=str(NEWS), help="RSS file to verify")
    args = parser.parse_args()
    run(Path(args.feed), args.apply)

if __name__ == "__main__":
    main()
