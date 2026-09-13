#!/usr/bin/env python3
"""Conservative headline/article-type classifier used before tab validation."""
from __future__ import annotations
import re

REVIEW=(re.compile(r'\breview\b',re.I), re.compile(r'\bhands[- ]on\b',re.I), re.compile(r'\bverdict\b',re.I))
GUIDE=(re.compile(r'\bhow to\b',re.I), re.compile(r'\bwalkthrough\b',re.I), re.compile(r'\bwhere to (?:find|buy|preorder|pre-order)\b',re.I), re.compile(r'\bcheats?\b',re.I))
LISTICLE=(re.compile(r'\btop \d+\b',re.I), re.compile(r'\bbest \d+\b',re.I), re.compile(r'\b\d+ best\b',re.I), re.compile(r'\btier list\b',re.I))
ANALYSIS=(re.compile(r'\banalysis\b',re.I), re.compile(r'\bexplainer\b',re.I), re.compile(r'\bwhat .* means\b',re.I), re.compile(r'\bwhy .* matters\b',re.I))
OPINION=(re.compile(r'\bopinion\b',re.I), re.compile(r'\beditorial\b',re.I), re.compile(r'\bcommentary\b',re.I))

def classify_article_type(title: str, description: str = '', url: str = '') -> str:
    text=' '.join((title or '',description or '',url or ''))
    if any(p.search(text) for p in OPINION): return 'opinion'
    if any(p.search(text) for p in REVIEW) or re.search(r'/reviews?/',url or '',re.I): return 'review'
    if any(p.search(text) for p in GUIDE): return 'guide'
    if any(p.search(text) for p in LISTICLE): return 'listicle'
    if any(p.search(text) for p in ANALYSIS): return 'analysis'
    return 'news'
