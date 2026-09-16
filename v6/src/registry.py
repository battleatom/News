from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "sources.json"
EXTRA_REGISTRY = ROOT / "config" / "sources-extra.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(payload: dict) -> dict:
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
    payload["source_count"] = len(sources)
    return payload


def load_registry(path: str | Path = DEFAULT_REGISTRY) -> dict:
    base_path = Path(path)
    payload = _load_json(base_path)
    if base_path.resolve() == DEFAULT_REGISTRY.resolve() and EXTRA_REGISTRY.exists():
        extra = _load_json(EXTRA_REGISTRY)
        payload["sources"] = [*payload.get("sources", []), *extra.get("sources", [])]
    return _validate(payload)
