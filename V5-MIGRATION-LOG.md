# Final V5 migration log

Baseline: hard-saved V4 commit `9549044575ac8ce8c17eccaa09702e157797b1cd` (`v4-hard-save-2026-09-12`).

## Baseline validation
- V4 structural audit: PASS.
- V4 inherited market / Entertainment / verifier regressions: PASS.
- Region normalization mismatch investigated: current policy intentionally uses `(30,35,80)` for Region and the current regression expects 80. The earlier `(30,35,40)` failure was a stale test expectation, so no runtime code change is justified.

## Fix 1 — editorial/category integrity and U.S. sports leakage
- Goal: prevent domestic/sports content in World/United States, route NFL-specific stories correctly, strengthen Technology/Gaming semantic routing, filter generic program/roundup landing pages, and validate related-coverage relevance.
- Optimization: consolidated these rules around one final editorial-integrity pass and shared classifier/federal/landing-page rules rather than adding another independent filter.
- Tests: inherited V4 audit/regressions + `tests/editorial_integrity_test.py` + `tests/us_sports_feed_check.py` + V4 diff/deletion guards.
- First attempt: correctly failed because the new landing-page detector found one V4 item before the cleanup transform ran.
- Harness correction: V5 transforms are now applied to a disposable candidate snapshot before the inherited audit. The detector was not weakened.
- Final result: PASS.

## Fix 2 — complete content briefs and story-specific Why It Matters
- Goal: replace V4's tab-wide canned impact language, prevent clipped/ellipsis summaries, preserve named subjects and concrete consequences, and keep fallbacks complete.
- Optimization: generate impact from structured story context while retaining deterministic rules; keep the existing V4 feed as the test input and regenerate Why It Matters in CI without doing network article fetches during each regression run.
- Test: `tests/story_context_regression_test.py` plus all previously enabled V5 tests.
- Status: pending CI.
