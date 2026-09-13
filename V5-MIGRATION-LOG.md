# Final V5 migration log

Baseline: hard-saved V4 commit `9549044575ac8ce8c17eccaa09702e157797b1cd` (`v4-hard-save-2026-09-12`).

## Baseline validation
- V4 structural audit: PASS.
- V4 inherited market / Entertainment / verifier regressions: PASS.
- Region normalization mismatch investigated: current policy intentionally uses `(30,35,80)` for Region and the current regression expects 80. The earlier `(30,35,40)` failure was a stale test expectation, so no runtime code change is justified.

## Fix 1 — editorial/category integrity and U.S. sports leakage
- Optimization: consolidated routing/filtering around one final editorial-integrity pass and shared classifier/federal/landing-page rules instead of adding another one-off filter.
- Initial failure: stronger landing-page detection found one V4 generic item before cleanup ran; test flow was corrected to audit the transformed V5 candidate without weakening detection.
- Tests: inherited V4 audit/regressions, editorial integrity, U.S.-sports feed check, diff/deletion guards.
- Result: PASS.

## Fix 2 — complete content briefs and story-specific Why It Matters
- Optimization: structured subject/event/affected-party/consequence logic replaces tab-wide canned impact text; briefs are complete rather than visually or textually clipped.
- CI avoids repeated network article fetching; it regenerates Why It Matters from the frozen feed and unit-tests brief generation deterministically.
- Tests: story-context/complete-brief regression plus all prior V5 tests and V4 guards.
- Result: PASS.

## Fix 3 — event clustering and cross-tab canonicalization
- Optimization: one event-identity layer handles exact/syndicated/semantic overlap instead of tab-specific duplicate scripts; cross-tab pruning has a 25% category-reduction safety ceiling.
- Performance optimization: full event clustering remains covered by its focused regression and final-build stage, while per-fix CI runs the fast conservative cross-tab pass on the full feed.
- Tests: event-cluster regression, feed-quality regression, fast cross-tab full-feed transform, all prior V5 tests and V4 guards.
- Result: PASS.

## Fix 4 — Underreported relevance and priority ranking
- Goal: rank Underreported by freshness, corroboration, coverage gap, momentum, continuing relevance, and event identity while rejecting low-value shopping/routine gaming items.
- Optimization: per-fix CI ranks the already collected V4 pool deterministically; network discovery and enrichment are retained for the final production build only.
- Test: `tests/underreported_priority_test.py` plus all prior V5 tests and V4 guards.
- Status: pending CI.
