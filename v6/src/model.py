from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

@dataclass(slots=True)
class Story:
    id: str
    category: str
    title: str
    url: str
    source: str
    published_at: str
    summary: str = ""
    why_matters: str = ""
    state: str = ""
    region: str = ""
    market: str = ""
    importance: float = 0.0
    source_id: str = ""
    what_happened: str = ""
    what_is_missing: str = ""
    background: str = ""
    what_next: str = ""
    coverage_label: str = ""
    coverage_score: int = 0
    coverage_gap_score: int = 0
    supporting_source_count: int = 0
    corroboration_score: int = 0
    freshness_score: int = 0
    coverage_momentum_score: int = 0
    continuing_relevance_score: int = 0
    saturation_penalty: int = 0
    underreported_priority: int = 0
    recent_supporting_sources_6h: int = 0
    recent_supporting_sources_24h: int = 0
    prior_supporting_sources_72h: int = 0
    related: list[dict[str, Any]] = field(default_factory=list)

    @property
    def published_dt(self) -> datetime:
        raw = (self.published_at or "").strip()
        if not raw:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
