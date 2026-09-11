#!/usr/bin/env python3
"""Neutral source-priority policy used only to choose a primary card.

This is intentionally not an ideology score. It prefers wire services with explicit
independence/impartiality standards, then major national/international straight-news
outlets, then other approved publishers. Political viewpoint is not used.
"""
from __future__ import annotations

# Higher is preferred when several approved outlets cover the same event.
# Reuters/AP are first because they are wire services whose published standards
# explicitly emphasize independence, accuracy, impartiality/freedom from bias.
SOURCE_PRIORITY = {
    "reuters": 100,
    "associated press": 100,
    "ap news": 100,
    "bbc": 90,
    "npr": 88,
    "cbs news": 86,
    "nbc news": 86,
    "abc news": 86,
    "fox news": 86,
    "cnn": 86,
    "usa today": 84,
    "the new york times": 84,
    "the washington post": 84,
    "politico": 82,
    "the hill": 82,
}


def source_priority(source: str | None) -> int:
    value = (source or "").strip().lower()
    return max((score for key, score in SOURCE_PRIORITY.items() if key in value), default=70)
