# Final V5 migration log

Baseline: hard-saved V4 commit `9549044575ac8ce8c17eccaa09702e157797b1cd` (`v4-hard-save-2026-09-12`).

## Baseline
- V4 structural audit and inherited market / Entertainment / verifier regressions: PASS.
- Region `(30,35,40)` assertion was stale; current policy/test intentionally uses `(30,35,80)`. No runtime change justified.

## Fix 1 — editorial/category integrity and U.S. sports leakage
- Consolidated final editorial-integrity routing/filtering and related-coverage checks.
- PASS.

## Fix 2 — complete briefs and story-specific Why It Matters
- Structured subject/event/affected-party/consequence logic replaces canned impact text; no deliberate brief clipping.
- PASS.

## Fix 3 — event clustering and cross-tab canonicalization
- One event-identity layer; retained duplicate coverage becomes supporting coverage; 25% category-reduction ceiling.
- Full clustering stays focused/final-build; per-fix CI uses fast cross-tab pass.
- PASS.

## Fix 4 — Underreported relevance and ranking
- Deterministic freshness/corroboration/coverage-gap/momentum/saturation/event ranking; network discovery remains final-build only.
- PASS.

## Fix 5 — X fixed-topic integrity
- Exactly ten fixed slots and a semantically relevant lead in each transformed slot.
- PASS.

## Fix 6 — Local/Region location behavior
- Local proves market relevance; Region follows detected state→region metadata; Farmington and false-positive cases pass.
- PASS.

## Fix 7 — NFL broadcast + streaming
- Streaming is a presentation layer after the canonical NFL renderer. Initial test failure was an escaped-quote assertion bug; implementation was unchanged for the passing rerun.
- PASS.

## Fix 8 — Entertainment clean public surface
- Clean and Dirty backing pools are retained, but public UI is Clean-only with no Dirty toggle/badge/marker.
- PASS.

## Fix 9 — canonical V5 build and runtime audit
- Goal: `build_site.py` must alone produce the complete final HTML, including Entertainment; eliminate the requirement for a post-build workflow mutation.
- Optimization: per-fix candidate generation now calls one canonical build instead of manually replaying individual UI patchers.
- Runtime blind spot fix: `v5_runtime_audit.py` inspects external assets, enforces one reference per required runtime controller, and ensures `app-v2.js` is the sole canonical-render wrapper owner while category surfaces use the renderer registry.
- Verifier integration: current V4 policy wrapper is retained because replacing its proven module-policy injection now would materially increase classification risk; the cross-tab guard is integrated into the final verifier and covered end-to-end. Recommend dependency-injected policy as a post-V5 refactor.
- Release gate and current normalized-pool contract are added to every V5 validation run.
- Status: pending CI.
