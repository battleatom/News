from __future__ import annotations
from dataclasses import dataclass, asdict
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
