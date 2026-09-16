from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "sources.json"

def load_registry(path: str | Path = DEFAULT_REGISTRY) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    categories = payload.get("categories", {})
    sources = payload.get("sources", [])
    if not categories:
        raise ValueError("source registry has no categories")
    seen = set()
    for source in sources:
        sid = str(source.get("id", "")).strip()
        category = str(source.get("category", "")).strip()
        if not sid or sid in seen:
            raise ValueError(f"invalid or duplicate source id: {sid!r}")
        if category not in categories:
            raise ValueError(f"source {sid} references unknown category {category!r}")
        if source.get("kind") not in {"google_news", "rss"}:
            raise ValueError(f"source {sid} has unsupported kind")
        if source.get("kind") == "google_news" and not source.get("query"):
            raise ValueError(f"source {sid} is missing a query")
        if source.get("kind") == "rss" and not source.get("url"):
            raise ValueError(f"source {sid} is missing a url")
        seen.add(sid)
    return payload
