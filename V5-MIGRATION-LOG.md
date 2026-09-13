# Final V5 migration log

Baseline: hard-saved V4 commit `9549044575ac8ce8c17eccaa09702e157797b1cd` (`v4-hard-save-2026-09-12`).

## Baseline validation
- V4 structural audit: PASS.
- V4 inherited market / Entertainment / verifier regressions: PASS.
- Region normalization mismatch investigated: current policy intentionally uses `(30,35,80)` for Region; the earlier `(30,35,40)` assertion was stale. No runtime change justified.

## Fix 1 — editorial/category integrity and U.S. sports leakage
- Consolidated routing/filtering around one final editorial-integrity pass and shared rules.
- Stronger landing-page detection initially exposed one V4 generic item; harness was corrected to audit the transformed candidate rather than weakening detection.
- Result: PASS.

## Fix 2 — complete content briefs and story-specific Why It Matters
- Structured subject/event/affected-party/consequence logic replaces tab-wide canned impact text; briefs are complete rather than clipped.
- Result: PASS.

## Fix 3 — event clustering and cross-tab canonicalization
- One event-identity layer handles repeated/syndicated coverage; cross-tab pruning has a 25% category-reduction safety ceiling and keeps removed copies as related coverage.
- Optimization: full clustering remains a focused/final-build test; per-fix CI uses the fast conservative cross-tab pass.
- Result: PASS.

## Fix 4 — Underreported relevance and priority ranking
- Per-fix CI deterministically ranks the existing pool; network discovery/enrichment stays final-build only.
- Result: PASS.

## Fix 5 — X fixed-topic integrity
- Exactly ten fixed topic slots; transformed feed must retain a semantically relevant lead in every slot.
- Result: PASS.

## Fix 6 — location-specific Local/Region behavior
- Goal: Local must prove city/market relevance, Statewide must include valid state-tagged local/region stories, and Region must follow the detected user's geographic region rather than a fixed region.
- Optimization: keep one nationwide inventory plus browser-side location scoping instead of maintaining per-city pages/feeds. Local uses city/market evidence; Region uses canonical state→region metadata.
- Per-fix test target: Farmington local relevance, false New Mexico/sports rejection, local-source/other-state rejection, Texas-region true/false cases, and controller wiring.
- Browser relative-region test is staged for final Playwright validation.
- Status: pending CI.
