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
- Goal: collapse same-event coverage into one primary card while retaining removed copies as supporting coverage, including conservative cross-tab duplicate removal.
- Optimization: one event-identity layer handles exact/syndicated/semantic overlap instead of adding tab-specific duplicate scripts; cross-tab pruning has a 25% category-reduction safety ceiling.
- Tests: event-cluster regression, feed-quality regression, residual cross-tab report, all prior V5 tests and V4 guards.
- Status: pending CI.
