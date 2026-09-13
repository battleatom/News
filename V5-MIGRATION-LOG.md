# Final V5 migration log

Baseline: hard-saved V4 commit `9549044575ac8ce8c17eccaa09702e157797b1cd` (`v4-hard-save-2026-09-12`).

## Baseline validation
- V4 structural audit: PASS.
- V4 inherited market / Entertainment / verifier regressions: PASS.
- Additional normalization test exposed a pre-existing V4 Region pool-policy mismatch: test expects `(30,35,40)`, V4 uses `(30,35,80)`. Logged for its own V5 fix; not allowed to contaminate unrelated fix results.

## Fix 1 — editorial/category integrity and U.S. sports leakage
- Goal: prevent domestic/sports content in World/United States, route NFL-specific stories correctly, strengthen Technology/Gaming semantic routing, filter generic program/roundup landing pages, and validate related-coverage relevance.
- Optimization decision: use one conservative final editorial-integrity module plus shared classifier/federal/landing-page rules instead of adding another independent one-off filter.
- Enabled regressions: `tests/editorial_integrity_test.py`, `tests/us_sports_feed_check.py`.
- Status: pending CI.
