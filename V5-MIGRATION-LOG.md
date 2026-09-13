# Final V5 migration log

Baseline: hard-saved V4 commit `9549044575ac8ce8c17eccaa09702e157797b1cd` (`v4-hard-save-2026-09-12`).

## Baseline validation
- V4 structural audit and inherited market / Entertainment / verifier regressions: PASS.
- Region `(30,35,40)` failure was a stale test expectation; current policy/test intentionally uses `(30,35,80)`. No runtime change justified.

## Fix 1 — editorial/category integrity and U.S. sports leakage
- Consolidated final editorial-integrity routing/filtering and related-coverage checks.
- Result: PASS.

## Fix 2 — complete briefs and story-specific Why It Matters
- Structured subject/event/affected-party/consequence logic replaces canned impact text; no deliberate brief clipping.
- Result: PASS.

## Fix 3 — event clustering and cross-tab canonicalization
- One event-identity layer; retained duplicate coverage becomes supporting coverage; 25% category-reduction ceiling.
- Optimized CI uses fast cross-tab pass; full clustering remains focused/final-build coverage.
- Result: PASS.

## Fix 4 — Underreported relevance and ranking
- Deterministic ranking covers freshness, corroboration, coverage gap, momentum, saturation, continuing relevance and event identity; network discovery remains final-build only.
- Result: PASS.

## Fix 5 — X fixed-topic integrity
- Exactly ten fixed slots and a semantically relevant lead in each transformed slot.
- Result: PASS.

## Fix 6 — location-specific Local/Region behavior
- Local proves market relevance; Region follows detected state→region metadata. Farmington and false-positive regressions pass.
- Result: PASS.

## Fix 7 — NFL broadcast + streaming availability
- Streaming is a presentation patch immediately after the canonical NFL renderer; no second sports data pipeline.
- First test run failed only because the assertion expected escaped quote characters. The candidate implementation had applied successfully; assertion corrected without changing NFL code.
- Result after corrected regression: PASS.

## Fix 8 — Entertainment clean public surface
- Goal: retain Clean and Dirty backing pools for data integrity while exposing only the Clean Entertainment surface in the public UI; no Dirty toggle/badge/marker.
- Optimization: keep one renderer and one backing feed; disable the Dirty UI path instead of creating separate pages or deleting retained Dirty records.
- Static integration test runs per-fix; full Playwright UI test is staged for final live validation.
- Status: pending CI.
